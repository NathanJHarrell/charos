# Swarm Validation Gate — Night of 2026-04-19

## What's Built (Infrastructure only — no live dispatch yet)

- `book-eating-engine/` — orchestrator plan + chapter-lead brief + section-worker brief + output structure spec
- `vault-atomization/` — same pattern applied to existing vault files
- Both reference the canonical multi-chapter-book-ingestion pattern from the Sub-Atomization taxonomy

## Prerequisites Still Open

1. **Tailscale auth on Jarvis** — Dad handling
2. **Epub corpus** — Dad dropping books into `~/Books/`
3. **Postgres reachable from Nest over Tailscale** — verify after Jarvis auth
4. **Ingestion pipeline on Jarvis** — confirm the Charmeleon-built ingestion script from earlier tonight is still runnable (chunker + embedder + upsert)

## Validation Walkthrough (before live dispatch)

### Book Engine
1. Pick ONE epub from `~/Books/`
2. Extract to plain text (pandoc or calibre-convert)
3. Run ONE chapter through ONE chapter-lead brief (manually, interactive — not headless)
4. TC reads the output files, verifies structure
5. Manually ingest into Postgres, run a test query, verify retrieval quality
6. THEN dispatch remaining chapters in parallel as headless Haikus

### Vault Atomization
1. Pick ONE vault file (something innocuous — not a `scrub: true` file)
2. Run through ONE file-worker brief (manually)
3. TC reviews the `.atoms/` output
4. Verify scrub inheritance on a `scrub: true` file
5. THEN dispatch full swarm

## Kill Switches

- If any atom contains text that wasn't in the source, STOP. No paraphrasing at atom level.
- If scrub inheritance fails on the test, STOP. Fix before continuing.
- If Postgres ingestion rate is pathological (>1s per atom), STOP — re-tune batch size.

## What Dad Wakes Up To (if all goes well)

- Nest family brain has N new book atoms + M new vault atoms
- He runs a test query and gets tight paragraph-level retrieval
- Decomposition-reasoning artifacts accumulating in `~/vault/meta/decomposition/canonical/`
