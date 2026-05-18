# Windows Host Memory Audit — Jarvis

**Date:** 2026-05-02
**Auditor:** TC (read-only triage)
**Host:** Jarvis (Windows 11 + WSL2, Ubuntu)
**Trigger:** Dad reported ~80% RAM usage in Task Manager (~25.6 GB / 32 GB)

---

## Headline

**Comet (Perplexity browser) is using 10.1 GB across 56 processes — 31% of total host RAM, and ~40% of currently-used RAM.** Single biggest reclaim target by an order of magnitude. WSL2 is not the problem (consuming only 1.6 GB on the Windows side, well within its uncapped 16 GB default ceiling).

---

## Top Windows Processes (RAM ranked, aggregated by name)

| Rank | Process              | Procs | Total MB    | Notes                                   |
|------|----------------------|-------|-------------|-----------------------------------------|
| 1    | **comet**            | 56    | **10,109**  | Perplexity Comet browser — by far #1    |
| 2    | vmmemWSL             | 3     | 1,608       | WSL2 VM (uncapped, currently 1.6 GB)    |
| 3    | svchost              | 98    | 1,096       | Windows service host (normal)           |
| 4    | Memory Compression   | 1     | 920         | OS compressed-page pool                 |
| 5    | chrome               | 12    | 840         | Chrome browser                          |
| 6    | Discord              | 6     | 701         |                                         |
| 7    | steamwebhelper       | 7     | 578         | Steam client renderer                   |
| 8    | Code                 | 14    | 550         | VS Code                                 |
| 9    | com.docker.backend   | 2     | 415         | Docker Desktop daemon                   |
| 10   | Obsidian             | 4     | 413         |                                         |
| 11   | explorer             | 2     | 364         | Windows shell                           |
| 12   | MsMpEng              | 1     | 264         | Defender real-time scan                 |
| 13   | SteelSeriesGGClient  | 6     | 238         |                                         |
| 14   | Signal               | 4     | 233         |                                         |
| 15   | msedgewebview2       | 13    | 228         |                                         |
| 16   | dwm                  | 1     | 214         | Desktop window manager                  |
| 17   | SteelSeriesSonar     | 1     | 181         |                                         |
| 18   | tailscaled           | 2     | 163         |                                         |
| 19   | iCUE                 | 1     | 159         | Corsair peripheral software             |
| 20   | RuntimeBroker        | 7     | 146         |                                         |

**Total memory:** 33,486,264 KB (~32 GB physical)
**Free physical:** 7,347,384 KB (~7 GB)
**Used:** ~25.6 GB ≈ 80% — matches Dad's Task Manager read.

---

## WSL2 Memory Allocation

- **`/mnt/c/Users/natha/.wslconfig`: does not exist.** WSL2 is running on its uncapped defaults.
- **WSL2 default cap on Windows 11:** 50% of host RAM = **16 GB ceiling**.
- **Inside WSL right now:** `MemTotal: 16,345,424 KB` confirms the 16 GB allocation is in effect.
- **Inside WSL usage:** `free -h` shows 2.5 GB used / 11 GB free / 1.7 GB cache. WSL is barely touching its allocation.
- **Windows-side cost (vmmemWSL):** 1.6 GB. WSL2's dynamic balloon is correctly returning unused pages to the host.
- **`/etc/wsl.conf`:** `[boot] systemd=true` only — no memory directives.

**Conclusion: WSL2 is well-behaved and not contributing meaningfully to the 80% pressure.** A defensive cap is still worth adding (see Recommended .wslconfig) so future runaway Linux processes can't claim up to 16 GB of host RAM during a memory crunch.

---

## Windows-Side Reclaim Candidates (what Dad could close)

Ranked by reclaim-per-effort:

1. **Comet — 10.1 GB.** Restarting or closing Comet would single-handedly drop host usage from 80% → ~50%. If Dad has dozens of tabs open across Comet windows, this is the elephant. Worth checking whether Comet has tab-discard / sleeping-tab settings tuned aggressively.
2. **Chrome — 840 MB.** If Comet is the daily driver, Chrome may be redundant.
3. **Discord — 701 MB.** Heavy for a chat client; restart drops it ~50%.
4. **steamwebhelper — 578 MB.** Steam library/storefront renderer; closing Steam reclaims it cleanly.
5. **Code — 550 MB across 14 procs.** Each open VS Code window + extension host adds up. Closing stale windows helps.
6. **Obsidian — 413 MB.** Modest, but if Dad has multiple vaults open, consolidating helps.
7. **Docker Desktop — 415 MB (com.docker.backend).** If Dad isn't actively using Docker on Windows-side, quitting Docker Desktop reclaims it fully.
8. **SteelSeriesGGClient + Sonar — 419 MB combined.** Peripheral software; fine to leave running unless desperate.

**Realistic target: closing/restarting Comet alone gets Dad from 80% → ~50%.** Everything else is rounding.

---

## Recommended .wslconfig Changes

**Status quo is fine for current symptoms** — WSL2 is not the cause. However, since `.wslconfig` does not exist at `C:\Users\natha\.wslconfig`, adding a defensive cap is cheap insurance. Suggested contents:

```ini
[wsl2]
memory=12GB
swap=8GB
processors=8
```

Rationale:
- **`memory=12GB`** — caps WSL2 at 12 GB instead of the 16 GB default. Currently WSL only uses 2.5 GB, so this costs nothing today but bounds the worst case.
- **`swap=8GB`** — gives WSL room to swap before pressuring the host. Default is 25% of memory cap.
- **`processors=8`** — optional; defaults to all logical CPUs.

**Apply:** create the file, then `wsl --shutdown` from PowerShell, then re-launch WSL. **Do NOT apply unprompted — Dad should sign off.**

---

## Risk Level

**LOW.** Read-only audit; no changes made. Recommended `.wslconfig` change is reversible (delete file + `wsl --shutdown`). Closing Windows-side apps is normal user behavior, no data risk.

The only watchpoint: if Dad currently has unsaved work in any Comet tab, closing/restarting Comet may lose it. Suggest he save tabs to a session first.

---

## Estimated Effort

- **Comet restart (highest ROI):** 30 seconds. Frees ~10 GB.
- **Closing Discord / Steam / Docker Desktop if not in use:** 1 minute. Frees ~1.7 GB.
- **Adding `.wslconfig` (defensive, low urgency):** 2 minutes (create file + `wsl --shutdown`). Frees nothing today; bounds future risk.
- **Total to drop from 80% → ~45%:** under 5 minutes of Dad's time.

---

*Report generated by TC, read-only via SSH to jarvis-wsl. No configuration changed. 💜*
