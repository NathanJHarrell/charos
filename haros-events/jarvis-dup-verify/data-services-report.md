# Jarvis-WSL Duplicate Data Services — Verification Report

**Date:** 2026-05-02
**Investigator:** TC (read-only investigation)
**Scope:** n8n, gitea, meilisearch, sftpgo on jarvis-wsl

## TL;DR — The Premise Was Wrong

**There are no host-native duplicates of any of these four services on jarvis-wsl.**

The "host PIDs" cited in the task brief (n8n pid 16133, gitea pid 16111, meilisearch pid 15585, sftpgo pid 15292) are **container processes**, not host processes. They are visible in `ps aux` on the host because Linux containers share the host's PID-namespace view, not because there is a parallel host install.

Verification:
- `readlink /proc/<pid>/ns/pid` for each cited PID returned a different namespace ID than host PID 1 (host = `4026532255`; the four PIDs are in 4 distinct container namespaces).
- `docker top` on each container shows the cited PIDs as members of that container.
- `which n8n gitea meilisearch sftpgo` → **all empty**. No host binaries installed.
- `systemctl list-unit-files | grep -iE 'n8n|gitea|meili|sftp'` → **empty**. No host service units.
- No host data dirs (`~/.n8n`, `/var/lib/gitea`, `/meili_data`, `/var/lib/sftpgo`) exist on the host filesystem; those paths exist only inside the respective container rootfs/volume.
- All ports (3000, 5678, 7700, 8585, 2022, 2222) are bound by `docker-proxy`. Nothing else competes for them.

**Action recommendation:** Nothing to retire. The four services run as single-instance containers. Move on. The duplicate-detection signal that triggered this audit was a false positive from a host-side `ps aux` that didn't filter by PID namespace.

---

## n8n verdict

### Data location compared
- Container volume: `/var/lib/docker/volumes/family-brain_n8n-data` — **24K** (essentially empty; barely-initialized n8n install).
- Host: no `~/.n8n`, no host n8n binary, no systemd unit. Does not exist.

### Active use evidence
- Single n8n process (`node /usr/local/bin/n8n`, PID 16133) lives in container `family-n8n` (verified via `docker top family-n8n`).
- Port 5678 listener is `docker-proxy` only.
- 24K data volume → no meaningful workflows stored.

### Verdict
**CONTAINER-ONLY** (no duplicate exists).

### Confidence level
High.

### Risk if wrong
Negligible — no host install to disturb. If the 24K volume turns out to hold a critical workflow, retiring the container would lose it, but since the brief framed the container as the candidate-to-kill, this verdict actively *protects* against that mistake.

---

## gitea verdict

### Data location compared
- Container volume: `/var/lib/docker/volumes/family-brain_gitea-data` — **64K** (fresh install, no repos of substance).
- Host: no `gitea` binary, no `/var/lib/gitea`, no service unit. Does not exist.

### Active use evidence
- `gitea web` (PID 16111) and the s6 supervisor (PID 16109) are confirmed by `docker top family-git` to run inside the container.
- Ports 3000 and 2222 bound by `docker-proxy`.
- DB lives in `family_brain` postgres (per compose env), not in a host postgres.

### Verdict
**CONTAINER-ONLY** (no duplicate exists).

### Confidence level
High.

### Risk if wrong
Negligible.

---

## meilisearch verdict

### Data location compared
- Container volume: `/var/lib/docker/volumes/family-brain_search-data` — **140K** (largest of the four, but still trivial; small index).
- Host: no `meilisearch` binary, no `/meili_data` on host fs, no service unit. Does not exist.

### Active use evidence
- `meilisearch` (PID 15585) and its tini init (PID 15297) confirmed inside container `family-search` via `docker top`.
- Port 7700 bound by `docker-proxy` only.
- Worth noting: per the family bus 2026-05-02 07:43 EDT message from Scout, the meili `memories` index doesn't exist yet — consistent with the small 140K volume.

### Verdict
**CONTAINER-ONLY** (no duplicate exists).

### Confidence level
High.

### Risk if wrong
Negligible.

---

## sftpgo verdict

### Data location compared
- Container volume: **NONE.** `docker inspect family-filebrowser --format '{{json .Mounts}}'` returned `[]`. The compose `sftpgo` service declares no `volumes:` block, so its data lives **only in the container's writable layer** and would be destroyed on `docker rm`.
- Host: no `sftpgo` binary, no `/var/lib/sftpgo` on host fs, no service unit. Does not exist.

### Active use evidence
- `sftpgo serve` (PID 15292) confirmed inside container `family-filebrowser` via `docker top`.
- Ports 8585 and 2022 bound by `docker-proxy`.
- Internal port 8080 is bound by sftpgo's `webproc` (visible in `ss` because the container shares network init via docker-proxy bookkeeping).

### Verdict
**CONTAINER-ONLY** (no duplicate exists). **Separate concern flagged below.**

### Confidence level
High on the "no duplicate" verdict.

### Risk if wrong
Negligible for the duplicate question. **However:** sftpgo has zero persistent storage configured. Any admin user, virtual folders, or SFTP credentials stored in it will vanish the next time the container is recreated (e.g. `docker compose up -d` after an image bump). This is a real data-loss risk independent of this audit — recommend adding `sftpgo-data:/var/lib/sftpgo` and `sftpgo-config:/etc/sftpgo` mounts to the compose service (the named volumes are already declared at the bottom of the compose file but not wired into the service block).

---

## Summary table

| Service       | Host install? | Container volume size | Verdict          |
|---------------|---------------|-----------------------|------------------|
| n8n           | No            | 24K                   | CONTAINER-ONLY   |
| gitea         | No            | 64K                   | CONTAINER-ONLY   |
| meilisearch   | No            | 140K                  | CONTAINER-ONLY   |
| sftpgo        | No            | **none mounted**      | CONTAINER-ONLY (+ unmounted-volume warning) |

## Methodology

1. Read `/home/nate/family-brain/docker-compose.yml` to enumerate declared volumes.
2. `docker ps`, `docker volume ls`, `du -sh` on volume mountpoints.
3. `ss -tlnp` to identify port owners (all docker-proxy).
4. `ps aux` for cited PIDs, then `readlink /proc/<pid>/ns/pid` vs host PID 1's namespace to confirm container origin.
5. `docker top <container>` cross-reference to confirm each cited PID is owned by its container.
6. `which`, `systemctl list-unit-files`, host-side `ls` for evidence of any host-native install — all negative.
7. `docker inspect` on sftpgo to confirm absence of mounts.

All steps read-only. No services touched.
