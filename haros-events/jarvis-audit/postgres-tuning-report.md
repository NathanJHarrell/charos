# Postgres Tuning Audit — family-brain @ jarvis-wsl

*Generated 2026-05-02 by TC. Read-only triage; no settings altered, no VACUUM run.*

## TL;DR

**The premise (RAM-constrained host, postgres needing tuning) does not match what's on the box.** Jarvis is at ~16% RAM use, family_brain DB is 13 MB total, the postgres container is sitting at 43 MB resident, and no table shows meaningful bloat. There is nothing to tune for RAM relief here. If anything, current settings are mildly oversized for the workload but not pinching anyone. Recommendation below is **leave it alone** with one optional baseline-tightening pass for hygiene.

## Host snapshot (jarvis-wsl)

```
Mem: 15Gi total, 2.4Gi used, 12Gi available, 1.7Gi buff/cache
Swap: 4.0Gi, 0B used
CPUs: 16
```

Container memory (docker stats, instant):

| Container | Mem | %  |
|-----------|-----|----|
| family-n8n         | 290 MB | 1.82% |
| family-git         |  88 MB | 0.55% |
| family-search      |  85 MB | 0.53% |
| family-scout       |  56 MB | 0.35% |
| **family-brain (postgres)** | **43 MB** | **0.27%** |
| family-tailscale   |  36 MB | 0.23% |
| family-filebrowser |  30 MB | 0.19% |
| family-caddy       |  26 MB | 0.16% |
| family-ntfy        |  24 MB | 0.15% |
| family-dns         |  21 MB | 0.13% |

Postgres is not in the top half of consumers. The "80% baseline" framing in the brief does not match this host's current state.

## Current Settings

| Setting | Value | Notes |
|---|---|---|
| shared_buffers | 128 MB | pgvector/postgres 17 default |
| work_mem | 4 MB | default |
| effective_cache_size | 4 GB | default |
| maintenance_work_mem | 64 MB | default |
| max_connections | 100 | default |
| wal_buffers | 4 MB | derived from shared_buffers |
| max_wal_size | 1 GB | default |
| checkpoint_completion_target | 0.9 | default |
| random_page_cost | 4 | HDD-era default; SSD wants 1.1 |
| effective_io_concurrency | 1 | low; SSD wants 200 |

These are stock postgres-17 defaults. Nobody has tuned this instance.

## Database + Table Sizes

Databases:

| DB | Size |
|---|---|
| family_brain | 13 MB |
| template1    | 7.4 MB |
| postgres     | 7.3 MB |
| template0    | 7.1 MB |

Top tables in family_brain:

| Table | Total | Heap | Live rows | Dead rows |
|---|---|---|---:|---:|
| memories                         | 1640 kB | 0 B    | 0   | 0  |
| role_scope                       | 128 kB  | 32 kB  | 465 | 0  |
| deployment_key                   | 104 kB  | 8 kB   | 4   | 0  |
| project_relation                 | 96 kB   | 8 kB   | 1   | 0  |
| migrations                       | 64 kB   | 16 kB  | 165 | 0  |
| scope                            | 64 kB   | 16 kB  | 189 | 1  |
| user                             | 64 kB   | 8 kB   | 1   | 4  |
| role                             | 48 kB   | 8 kB   | 15  | 15 |
| workflow_dependency              | 48 kB   | 0 B    | 0   | 0  |
| frameworks                       | 48 kB   | 8 kB   | 4   | 0  |
| execution_entity                 | 48 kB   | 0 B    | 0   | 0  |
| citizens                         | 48 kB   | 8 kB   | 11  | 0  |

The `memories` table (the pgvector target) is empty — consistent with Scout's 2026-05-02 07:43 EDT bus message about brain-web's vector-dimension mismatch (column is vector(1536), embeddings produced at 384). It hasn't ingested anything.

**No `binary_data` table.** n8n in this household runs in `family-n8n` against its own SQLite store, not against family-brain. The `workflow_entity` / `execution_entity` rows you see in family_brain are a different schema (citizen / brain-web, not n8n) and are empty.

## Tuning Recommendations

**Primary recommendation: do nothing.** The DB is 13 MB and the host has 12 GB free. Tuning shared_buffers up or work_mem down won't reclaim RAM that isn't being used, and won't make queries faster on tables that fit in L3.

If you want a hygiene-pass anyway (cheap, low-risk, mostly future-proofing for when `memories` actually populates):

| Setting | Current | Suggested | Reasoning |
|---|---|---|---|
| random_page_cost | 4 | **1.1** | Jarvis storage is SSD/NVMe; the 4-vs-1.1 gap changes plan choice (index scan vs seqscan) on tables once they grow. Free correctness fix. |
| effective_io_concurrency | 1 | **200** | SSD; lets bitmap heap scans prefetch. Free perf on future bigger queries. |
| effective_cache_size | 4 GB | **8 GB** | Hint only — tells planner how much OS cache it can assume. With 12 GB free, 4 GB is a pessimistic hint. Doesn't allocate memory. |
| shared_buffers | 128 MB | leave at 128 MB (or 256 MB if `memories` starts filling) | No reason to grow it for a 13 MB DB. Revisit when memories table crosses ~500 MB. |
| work_mem | 4 MB | leave | pgvector ANN queries can want more, but raise per-session via `SET work_mem` rather than globally — global raise × 100 connections is the footgun. |
| maintenance_work_mem | 64 MB | **256 MB** | Only used during VACUUM/CREATE INDEX/REINDEX. Speeds up the ivfflat rebuild Scout flagged. Allocated only when those run. |
| max_connections | 100 | leave | No pressure. |

All of the above are reload-safe except shared_buffers (restart required if changed). None reclaim RAM — they shape behavior when the DB grows.

## VACUUM Candidates

**None worth running.** Highest dead-tuple counts:

- `role`: 15 live / 15 dead — autovacuum will pick this up on its own threshold; manual VACUUM saves nothing meaningful (table is 48 kB).
- `user`: 1 / 4
- `scope`: 189 / 1
- `project`: 1 / 1

These are rounding error. No bloat. Skip.

When `memories` fills and starts churning embeddings, **then** a periodic `VACUUM ANALYZE memories` + ivfflat reindex will matter. Not now.

## Expected RAM Reclaim

**~0 MB.** Postgres is using 43 MB. There is no RAM to reclaim. The 11 GB of free memory on jarvis is not held by postgres; it's genuinely free (plus 1.7 GB in OS buff/cache, which is correct behavior, not waste).

If the original concern was "jarvis feels memory-pressured," postgres is not the suspect. The biggest consumer is family-n8n at 290 MB, and that's still trivial. Look at non-container processes (the WSL2 VM itself, vmmem on the Windows side) before blaming any container.

## Risk Level

- **Doing nothing: zero risk.** Recommended.
- **Hygiene-pass tuning above: very low risk.** All planner hints + maintenance-time settings; no behavior change for current empty workload. random_page_cost change is the only one that can flip plans, and on an empty/tiny DB it won't.
- **Restart for shared_buffers change: low risk** but unnecessary — would briefly drop the brain-web HTTP layer.

## Estimated Effort

- Do nothing: 0 minutes.
- Apply hygiene pass via `ALTER SYSTEM SET ... ; SELECT pg_reload_conf();` (no restart needed for any of the suggested values except shared_buffers, which we're not changing): **~5 minutes** end-to-end including a sanity SELECT to confirm reload.
- Re-audit after `memories` table populates with real ingest traffic: **~15 minutes** to re-run this report against a non-empty DB and re-decide shared_buffers/work_mem.

## Side notes surfaced during audit

1. **Scout's 07:43 EDT bus message is corroborated** — `memories.embedding` column is dimensionality-mismatched against the ingest model. The two-line fix Scout proposed is still the right call. This is a schema bug, not a tuning bug.
2. **`role scout does not exist`** — also flagged by Scout. Some daemon is auth-attempting as `scout` and failing. Out of scope for this report but worth pairing with the dim-fix work.
3. **n8n binary_data is not in this database.** If n8n ever gets pointed at family-brain (env var `DB_TYPE=postgresdb`), revisit this report — that's the table that historically eats space.
