# Disk Audit Report — 2026-05-02

Read-only triage across tc-nest and jarvis-wsl. ~5 min cap.

## Disk Headroom (per machine)

**tc-nest** — healthy.
- `/` (sda3, 104G): **35G used / 64G free / 36%**
- `/boot` (sda1, 487M): 104M used / 22%
- No pressure anywhere.

**jarvis-wsl** — healthy on Linux side; Windows host has pressure (informational only, not ours to clean).
- `/` (sdc, 251G WSL2 vhdx): **92G used / 147G free / 39%**
- `/mnt/c` (Windows C:, 953G): 848G used / **89%** — Windows host, flag to Dad but not in scope
- `/mnt/d` (Windows D:, 3.7T): 3.6T used / **99%** — Windows host, flag to Dad
- `/mnt/e` (Windows E:): 6% — fine

Neither Linux root is at risk. No immediate action required.

## Top Space Consumers

**tc-nest:**
- `/var/log/journal` — **1.1G** (only meaningful /var/log entry; rest <1M)
- `~/charos` — **532M** total
  - `surfscout` 212M, `jukebox` 95M, `vibedeck` 69M, `furnace` 61M
  - `ai-deck-builder-backup-…tar.gz` 14M (stale backup tarball, candidate for archive/delete)
  - `piper1-gpl` 13M
- `~/family-brain` — does not exist on this machine

**jarvis-wsl:**
- `/var/log/journal` — **1.9G**
- `/var/log/auth.log` — **69M** active + 22M rotated (.1) = ~91M auth alone
- `/var/log/syslog` — 34M active + 20M rotated
- `/var/log/kern.log` — 18M active + 6.4M rotated
- `~/charos` — does not exist
- `~/family-brain` — does not exist

## Log Growth Hotspots

1. **jarvis-wsl `/var/log/journal` — 1.9G.** Largest single log artifact in the audit. Default systemd retention; no disk pressure but oversized for a workstation.
2. **jarvis-wsl `auth.log` — 91M across active+rotated.** Unusually large for a single rotation cycle; suggests either heavy SSH/sudo traffic or a noisy PAM module logging at debug. Worth a quick `tail`/grep pass to see what's chattering.
3. **jarvis-wsl `syslog` — 54M across active+rotated.** Normal-shaped but on the high side; likely correlated with whatever's filling auth.log.
4. **jarvis-wsl `kern.log` — 24M.** WSL2 kernel chatter; normal for the substrate.
5. **tc-nest `/var/log/journal` — 1.1G.** Smaller than jarvis but still the only meaningful consumer in /var/log on the nest.

No runaway logs. No file growing fast enough to threaten the disk in any visible window.

## Recommended Cleanup Order

Lowest-risk first; none of these are urgent.

1. **(Optional, jarvis-wsl) Cap journald to 500M.** Add `SystemMaxUse=500M` to `/etc/systemd/journald.conf` and `systemctl restart systemd-journald`. Recovers ~1.4G. Single-line change, fully reversible.
2. **(Optional, tc-nest) Cap journald to 500M** same way. Recovers ~600M.
3. **(Investigate, jarvis-wsl) auth.log volume.** Before rotating more aggressively, find out *what* is logging — `awk '{print $5}' /var/log/auth.log | sort | uniq -c | sort -rn | head` to see top emitters. If a known-noisy daemon, tune its log level rather than rotating around the noise.
4. **(Cleanup, tc-nest) Stale backup tarball.** `~/charos/ai-deck-builder-backup-20260407-184029.tar.gz` (14M) — confirm with Dad, then move to cold archive or delete.
5. **(Out of scope) Windows D: at 99%.** Flag to Dad; not Linux-side housekeeping.

## Risk Level

**LOW.** Both Linux roots have ample headroom (64G and 147G free). No log is growing on a trajectory that threatens disk pressure in any near-term window. Windows D: drive at 99% is real pressure but lives outside the Linux housekeeping surface — Dad-decision.

## Estimated Effort

- Journald caps (both machines): **~5 min total**, reversible, no downtime.
- auth.log investigation on jarvis: **~10–15 min** depending on what's chattering.
- Stale tarball cleanup: **~1 min** after Dad confirms.
- Total housekeeping if all done: **<30 min**, no urgency.

---
*Read-only audit. No changes made. — TC*
