# Jarvis WSL2 Memory Audit — Internal View

**Date:** 2026-05-02 08:14 EDT
**Auditor:** TC (read-only triage from inside jarvis-wsl via SSH)
**Headline:** **No memory pressure exists inside the Linux guest.** WSL2 sees 15 GiB total, 2.4 GiB used, **12 GiB available**, swap untouched (0 / 4 GiB). If the host Windows side is reporting pressure, the cause is the WSL2 VM size cap or other Windows processes — not anything starving inside Linux.

```
total        used        free      shared  buff/cache   available
15Gi        2.4Gi        11Gi        27Mi       1.7Gi        12Gi
```

`/etc/wsl.conf` only contains `[boot] systemd=true` — **no `[wsl2] memory=` cap is set**, so the guest is taking whatever Windows allocates dynamically (default ~50% of host RAM). Tunable lever exists if Windows needs the cap raised/lowered.

---

## Top RAM Consumers

Linux processes (RSS) and Docker containers, merged and sorted:

| Rank | Process / Container               | RSS / MEM USAGE | Where         | Notes |
|-----:|-----------------------------------|----------------:|---------------|-------|
| 1    | `brain-web.py` (uvicorn)          | **829 MB**      | host          | Running as `tc-nest` user, port unknown — biggest single consumer by far |
| 2    | `family-n8n` container            | 290 MB          | docker        | n8n service in container |
| 3    | `n8n` (host node)                 | **268 MB**      | host          | **DUPLICATE n8n running on host** outside container — pid 16133 user `nate` |
| 4    | `dockerd`                         | 175 MB          | host          | engine itself |
| 5    | `gitea web`                       | 149 MB          | host          | running native, not the `family-git` container |
| 6    | `n8n task-runner` (host)          | 126 MB          | host          | child of host-n8n |
| 7    | `tailscaled` (host)               | 109 MB          | host          | |
| 8    | `subiquity.cmd.server`            | 110 MB          | host          | **Ubuntu-desktop-installer leftover** — should not be running on a long-lived box |
| 9    | `meilisearch` (host)              | 104 MB          | host          | duplicates `family-search` container (85 MB) |
| 10   | `family-git` container            | 88.5 MB         | docker        | duplicates host gitea |
| 11   | `family-search` container         | 85 MB           | docker        | duplicates host meilisearch |
| 12   | `uvicorn api.main:app :8000`      | 76 MB           | host          | unidentified API |
| 13   | `sftpgo serve` (host)             | 62 MB           | host          | duplicates `family-filebrowser` container (29 MB, also sftpgo) |
| 14   | `uvicorn server:app :4318`        | 61 MB           | host (nate)   | unidentified |
| 15   | `caddy` (host)                    | 59 MB           | host          | duplicates `family-caddy` container (26 MB) |
| 16   | `ntfy serve` (host)               | 52 MB           | host          | duplicates `family-ntfy` container (23 MB) |
| 17   | `dnsmasq webproc` (host)          | 22 MB           | host          | duplicates `family-dns` container (21 MB) |

**Container totals (all 10 family-* containers):** ~700 MB combined. Trivial.

**The real signal:** the host has its own parallel copy of nearly every containerized service (n8n, gitea, meilisearch, sftpgo, caddy, ntfy, dnsmasq). That's the structural waste — not container bloat.

---

## Forge

- `/home/nate/forge/` exists, last modified 2026-04-26.
- **No Next.js / forge process running.** `pgrep -af "next|forge"` returned nothing.
- Forge is currently consuming 0 RAM. Not a candidate.

---

## n8n Activity

- `family-n8n` container DB lookup failed (no sqlite3 in container; n8n has migrated to its mounted DB elsewhere).
- `n8n list:workflow` returned empty output (likely needs auth env or the host n8n owns the data).
- Host n8n + container n8n **both running simultaneously** — at minimum one is dead weight. Cannot determine active workflow count without credentialed access.

---

## chat_hub_* Tables (in `family_brain` Postgres)

```
sessions: 0    messages: 0    agents: 0
```

**Completely dormant.** No users table even exists. The 6 tables (`chat_hub_agents`, `chat_hub_agent_tools`, `chat_hub_messages`, `chat_hub_session_tools`, `chat_hub_sessions`, `chat_hub_tools`) hold zero rows. Schema scaffolding only.

Also noted while there: **one idle-in-transaction (aborted) postgres connection** from `family_brain` (pid 16605) — minor, but a sign of a client that didn't clean up. Likely tied to Scout's earlier brain-web 500 root cause (the 1536-vs-384 dim mismatch he flagged on the bus at 07:43).

---

## Dormant Services (candidates for shutdown)

| Service | Why dormant | RAM saved |
|---|---|---|
| **subiquity.cmd.server** (Ubuntu installer) | Installer leftover running on a fully-installed long-lived host | ~110 MB |
| **Host-side n8n** (pid 16133 + 16210 task-runner) | `family-n8n` container exists for the same purpose; running both is duplication | ~390 MB |
| **Host-side gitea** | `family-git` container exists | ~149 MB |
| **Host-side meilisearch** | `family-search` container exists | ~104 MB |
| **Host-side sftpgo** | `family-filebrowser` container is also sftpgo | ~62 MB |
| **Host-side caddy** | `family-caddy` container exists | ~59 MB |
| **Host-side ntfy** | `family-ntfy` container exists | ~52 MB |
| **Host-side dnsmasq** | `family-dns` container exists | ~22 MB |
| **chat_hub_* schema** | 0 rows everywhere — never used | negligible RAM, but indicates dead code path |

---

## Top 5 Reduction Candidates

1. **Decide host-vs-container for n8n and shut down one side.** ~290 MB or ~390 MB freed depending on which wins. Host n8n (pid 16133) has a task-runner child also using 126 MB. Risk: workflows live on whichever side has the DB — verify before killing.
2. **Stop `subiquity.cmd.server`.** Ubuntu installer subiquity has no business running on a provisioned box. ~110 MB. Risk: low (it's a finished installer).
3. **Pick a side for gitea (host vs `family-git`).** ~149 MB or ~89 MB. Risk: medium — gitea repos live on whichever side has the data dir mounted.
4. **Pick a side for meilisearch / sftpgo / caddy / ntfy / dnsmasq.** Aggregate ~300 MB if host-side copies retire. Risk: medium per service — some host-side instances may be the production one (caddy on host serves local TLS for tailnet certs, common pattern).
5. **Investigate `brain-web.py` 829 MB footprint.** It's the single biggest process and Scout already flagged it as broken (vector-dim mismatch making it 500 on every query). A broken service should not be the largest RAM consumer. Either fix per Scout's recipe (`ALTER COLUMN embedding TYPE vector(384)`) or stop it until repaired. Risk: low — it's already non-functional.

---

## Linux + Docker Reclaim Estimate

- **Realistic reclaim** if all duplicate host-side daemons retire in favor of containerized equivalents: **~870 MB**.
- **Plus subiquity:** ~980 MB total.
- **Plus brain-web shutdown:** ~1.8 GB total.

Against a current 2.4 GB used baseline, that's a ~75% reduction — but again, **there is no internal pressure to relieve.** This is a hygiene exercise, not a rescue.

---

## Risk Level (per recommendation)

| Recommendation | Risk |
|---|---|
| Stop `subiquity.cmd.server` | **Low** |
| Stop broken `brain-web.py` (or fix per Scout) | **Low** |
| Retire host-side n8n (or container) | **Medium** — verify which holds workflows |
| Retire host-side gitea (or container) | **Medium** — verify repo data location |
| Retire host-side meilisearch / caddy / ntfy / dnsmasq / sftpgo | **Medium** — caddy especially may be load-bearing for tailnet TLS |
| Drop `chat_hub_*` schema | **Low** — zero data, but verify no in-flight code expects the tables |
| Adjust WSL2 `[wsl2] memory=` cap | **Low** — Windows-side knob, easy to revert |

---

## Estimated Effort

- **Low (≤30 min total):** kill subiquity, stop brain-web, decide WSL2 memory cap.
- **Medium (1–2 hrs):** audit which n8n/gitea/meili/etc. holds the canonical data, decommission the loser, update Caddy/DNS to point at the survivor.
- **Higher (half-day):** if a real `wsl --shutdown` + `[wsl2] memory=` retune is wanted, plus full host-vs-container consolidation with verified service health afterward.

---

## What This Audit Did NOT Touch

- Did not stop, restart, or reconfigure any service.
- Did not modify `/etc/wsl.conf` or `/etc/fstab`.
- Did not write to the Jarvis filesystem (could not — SSH user `tc-nest` lacks write under `/home/nate/charos/`). Report written to **tc-nest** at the requested path instead.

---

*— TC, 2026-05-02 08:14 EDT*
