# Family-Brain Vector Dimension Mismatch — Triage Report

**Host:** jarvis-wsl
**Date:** 2026-05-02
**Mode:** read-only triage

## Root Cause

Schema/code mismatch in `/home/nate/family-brain/`:

- **Schema** (`init/*.sql`, applied to live DB): `embedding vector(1536)` on `memories`, `frameworks`, and two other tables. 1536 is the OpenAI `text-embedding-ada-002` / `text-embedding-3-small` dimension — a leftover from an earlier design.
- **Code** (`ingest.py:33` and `query.py:30`): `EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`, which produces **384-d** vectors. Both ingest and query use the same local model.
- **Live DB state** (`docker exec family-brain psql ...`): `memories` has 0 rows; `frameworks` has 0 rows with embeddings populated. **No corpus exists yet.** The mismatch surfaces at query time because the cast `%s::vector` against a `vector(1536)` column rejects a 384-d input — the error fires before any row is compared.

So this is **not** drift between stored data and current code. Ingest has never successfully written an embedding (it would have failed with the same dimension error on first INSERT). Query is simply the first place anyone noticed.

**The code is correct; the schema is stale.**

## Recommended Fix

Reconcile schema down to 384-d to match MiniLM-L6-v2. Two options, in order of preference:

1. **(Preferred)** Edit `init/*.sql` to declare `vector(384)` everywhere, then drop & recreate the four affected tables (`memories`, `frameworks`, and the two others surfaced by grep). Since all tables are empty, this is a clean reset — no data loss, no migration scaffolding needed. Re-run `ingest.py` to populate.
2. **(If init is read-only / volume-baked)** Issue an in-place migration:
   ```sql
   DROP INDEX idx_memories_embedding;
   ALTER TABLE memories ALTER COLUMN embedding TYPE vector(384);
   CREATE INDEX idx_memories_embedding ON memories
       USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
   ```
   Repeat for the other three tables. Still safe because they're empty.

**Do NOT** swap the code to a 1536-d model (e.g. OpenAI ada). Reasons:
- ingest.py is explicitly designed for local/offline embedding (`SentenceTransformer`, no API key plumbed in env).
- Family-brain runs on private vault content; sending it to OpenAI changes the trust posture.
- MiniLM-L6-v2 is the right call for this corpus size and latency target.

## Risk Level

**Low.**

- No data at risk — both `memories` and `frameworks` embedding population are empty.
- No live consumers depending on stored vectors (nothing's been queryable since the corpus is empty).
- Schema change is a drop-and-recreate on empty tables; reversible.
- Only side effect: re-running `ingest.py` rebuilds from the vault, which is the source of truth.

Watch-outs:
- Confirm the `frameworks`, `dinners`, and any other tables in `init/` follow the same pattern before issuing the migration — grep showed four `vector(1536)` declarations.
- The `ivfflat` index needs to be dropped before `ALTER COLUMN TYPE` and recreated after, otherwise PG rejects the change.

## Estimated Effort

**~15 minutes**, hands-on:
- 2 min: edit `init/*.sql` (1536 → 384, 4 occurrences)
- 3 min: drop & recreate the four tables (or run the in-place ALTER for each)
- 5 min: run `ingest.py` against the vault and confirm row counts > 0
- 5 min: smoke-test `query.py "Vesper"` and confirm semantic results return

No coordination needed beyond Dad's go-ahead — this is a local schema fix on jarvis-wsl with no shared-state blast radius.
