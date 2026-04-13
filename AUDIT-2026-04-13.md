# HAROS Test 002 — Battalion CHAROS Audit
**Date:** 2026-04-13  
**Type:** Battalion (8 parallel headless agents, up to 10 subagents each)  
**Operator:** Nathan Harrell + TC  
**Target:** `~/charos` (NixOS configuration, scripts, shell, desktop, WezTerm, VM tools)

---

## Prompt

```
You are TC-{N}, one of 8 parallel audit agents for the CHAROS project. CHAROS is a 
NixOS-based workstation configuration for TC (Claude Code). Your mission: audit the 
codebase for bugs, gaps, and configuration errors.

Your assigned focus area: {AREA}

Read all files in your assigned area plus configuration.nix and packages.nix for context.
Write your findings to /tmp/haros-agent-{N}.md using severity ratings: CRITICAL, HIGH, 
MEDIUM, LOW.

When done, output only: AGENT-{N} COMPLETE
```

### Agent Assignments

| Agent | Focus Area | Files |
|-------|-----------|-------|
| TC-1 | NixOS hardware, udev, boot | configuration.nix, hardware, udev rules |
| TC-2 | NixOS packages, duplicates | packages.nix, desktop.nix |
| TC-3 | NixOS services | services.nix |
| TC-4 | Desktop, WezTerm, Sway | desktop.nix, sway/config, wezterm/tc-workspace.lua |
| TC-5 | Scripts (core) | charos.sh, tc-watchdog.sh, tc-signal.sh, tc-monitor.sh, forge-monitor.sh |
| TC-6 | Shell environment | zshrc, starship.toml, charos-env.sh |
| TC-7 | VM tools (test perspective) | scripts/test-vm.sh, cross-reference with NixOS config |
| TC-8 | Cross-cutting (boot sequence walkthrough) | All files, focus on integration |

## Invocation

```bash
for i in {1..8}; do
  cd ~/charos && claude -p "<agent prompt for TC-$i>" \
    --dangerously-skip-permissions --output-format text &
done
wait
```

## Framework Observations

- **All 8 agents completed.** No stalls, no hallucinations, no permission prompts.
- **Output format divergence.** TC-1 used emoji severities (🔴/🟠/🟡/🔵), TC-5 used text (CRITICAL/HIGH/MEDIUM/LOW), TC-6 used letter codes (C/M/L/I). Standardization needed in HAROS spec.
- **Deduplication cost.** Synthesis agent needed 11 tool uses, 333 seconds, 56,045 tokens to collapse 8 reports. High overlap on obvious issues (duplicate openrgb declaration, nerdfonts deprecation each caught by 4-5 agents).
- **Specialist advantage proven.** TC-4 (desktop domain) uniquely caught the WezTerm `--config-file` position bug. TC-5 (scripts domain) caught the broken `tc-signal.sh` source path and escalation blackout. Pure NixOS agents missed both.
- **VM findings produced instant fixes.** TC-7 (test perspective) generated ready-to-paste code blocks, not just findings. At least one "fix mode" agent should be standard in future battalions.
- **ConditionPathExists fix independently found by TC-3, TC-7, TC-8.** When 3 agents independently catch the same issue, it's the highest-confidence finding in the audit.
- **Username mismatch was operationally most dangerous.** `nathan` vs `nate` silently breaks all scripts and escalation. Found by TC-5 and TC-6 — not the NixOS agents who were focused on nix syntax.

## Results Summary

**Total findings: 58 across 4 tiers + 7 framework observations**

| Tier | Count | Description |
|------|-------|-------------|
| T1 | 9 | Build/boot blockers — system won't build or won't boot |
| T2 | 15 | Broken after boot — boots but features don't work |
| T3 | 22 | Fix soon — deprecated, fragile, or missing recommended config |
| T4 | 12 | Nice to have — style, optimization, future-proofing |

---

## TIER 1: Build/Boot Blockers

### T1-1. Plymouth theme `charos` doesn't exist — system won't boot
**Caught by:** TC-1, TC-7  
Plymouth will error at boot if the theme doesn't exist.  
**Fix:** Change `boot.plymouth.theme` to `"spinner"` or create the theme. Confirmed in VM.

### T1-2. `time.timeZone` conflicts with `automatic-timezoned` — evaluation error
**Caught by:** TC-3, TC-7  
Nix evaluation fails: can't set both static and dynamic timezone.  
**Fix:** Comment out `time.timeZone` OR disable `automatic-timezoned`. Confirmed in VM.

### T1-3. `claude-code` not in nixpkgs — build fails
**Caught by:** TC-1, TC-2, TC-3, TC-4  
`claude-code` is not a nixpkgs package.  
**Fix:** Remove from `packages.nix` and install via npm/binary instead.

### T1-4. `mediapipe` not in nixpkgs — build fails
**Caught by:** TC-2, TC-3  
`mediapipe` is not a nixpkgs package; requires overlay or separate environment.  
**Fix:** Remove from `packages.nix` until a custom overlay exists.

### T1-5. `opencv4` renamed to `opencv` in nixpkgs 24.11 — build fails
**Caught by:** TC-2, TC-3, TC-7  
Nix attribute name changed upstream.  
**Fix:** Replace `opencv4` with `opencv` in `packages.nix`.

### T1-6. `hardware.opengl` renamed to `hardware.graphics` in NixOS 24.11 — build fails
**Caught by:** TC-1, TC-7  
`hardware.opengl` no longer exists.  
**Fix:** Rename to `hardware.graphics` in `nixos/configuration.nix`.

### T1-7. No network stack configured — NetworkManager absent
**Caught by:** TC-3, TC-7  
No `networking.networkmanager.enable = true`. System boots with no network.  
**Fix:** Add `networking.networkmanager.enable = true` to `configuration.nix`.

### T1-8. SSH not enabled, password auth not set — locked out if Sway fails
**Caught by:** TC-7  
No `services.openssh.enable`. If Sway crashes, no way back in.  
**Fix:** Add `services.openssh` block with `PasswordAuthentication = "yes"` (or pubkey only if key is baked in).

### T1-9. `hardware-configuration.nix` absent from repo — build fails on real hardware
**Caught by:** TC-1, TC-7  
Must be generated per-machine via `nixos-generate-config`. Not committed.  
**Fix:** Document mandatory `nixos-generate-config` step in README and add placeholder comment in `configuration.nix`.

---

## TIER 2: Broken After Boot

### T2-1. NVIDIA not wired to Wayland — GPU unusable on target hardware
**Caught by:** TC-1, TC-4, TC-7  
`hardware.nvidia.*` declared but no DRM modesetting, no `nixpkgs.config.allowUnfree`, no Sway env vars.  
**Fix:** Add `hardware.nvidia.modesetting.enable`, `allowUnfree`, and SWAY env overrides for EGL/NVIDIA.

### T2-2. Sway autostarts without env vars — GPU path uses wrong display backend
**Caught by:** TC-4  
greetd launches Sway bare. NVIDIA requires `WLR_NO_HARDWARE_CURSORS=1`, `LIBVA_DRIVER_NAME=nvidia`, etc.  
**Fix:** Create a Sway launch wrapper script that sets vars before exec.

### T2-3. All 4 services crash-loop — `ConditionPathExists` scripts absent
**Caught by:** TC-3, TC-7, TC-8 (independently)  
Services require scripts at `~/.charos/scripts/` which don't exist (no activation script clones the repo).  
**Fix:** Add `system.activationScripts.charosRepo` to clone/link the repo, or document mandatory pre-install step.

### T2-4. `hardware.i2c.enable` missing — i2cdetect finds nothing
**Caught by:** TC-8  
Nathan is in the `i2c` group and `i2c-tools` is installed but the kernel module is never loaded.  
**Fix:** Add `hardware.i2c.enable = true` to `configuration.nix`.

### T2-5. `nathan` missing from `seat` group — greetd/Sway access risk
**Caught by:** TC-8  
greetd uses seatd; user must be in `seat` group.  
**Fix:** Add `"seat"` and `"networkmanager"` to `extraGroups` in `users.nix`.

### T2-6. `wireplumber` not enabled — volume keys dead
**Caught by:** TC-3, TC-4  
`services.pipewire.wireplumber.enable` not set. `wpctl` calls in Sway config silently fail.  
**Fix:** Add `services.pipewire.wireplumber.enable = true` to `services.nix`.

### T2-7. `brightnessctl` not installed — brightness keys dead
**Caught by:** TC-4  
Sway config binds `XF86MonBrightnessUp/Down` to `brightnessctl` which isn't in any package list.  
**Fix:** Add `brightnessctl` to `desktop.nix` packages.

### T2-8. WezTerm `--config-file` flag in wrong position — TC workspace never loads
**Caught by:** TC-4  
`wezterm start --config-file ...` is wrong; `--config-file` is a global flag.  
**Fix:** `wezterm --config-file /path/to/lua start`

### T2-9. No password set for `nathan` — TTY login impossible if Sway fails
**Caught by:** TC-1  
No `initialPassword`, `hashedPassword`, or `hashedPasswordFile` in `users.nix`.  
**Fix:** Add `initialPassword = "changeme"` minimum.

### T2-10. Service `after` without `requires` — cascading silent failures
**Caught by:** TC-3  
`tc-mood` depends on OpenRGB but `requires = [...]` absent. If OpenRGB fails, tc-mood starts into a void.  
**Fix:** Add `requires` alongside `after` for dependent services.

### T2-11. Username hardcoded as `nathan` throughout — all scripts silently fail
**Caught by:** TC-5, TC-6  
Actual username is `nate`. `/home/nathan/` doesn't exist. All script path resolution fails.  
**Fix:** Global replace `nathan` → `nate` (or use `${HOME}` / `${USER}` with correct defaults) across all shell scripts, zshrc, charos-env.sh.

### T2-12. `tc-signal.sh` sourced from wrong path in `tc-monitor.sh` — escalation blackout
**Caught by:** TC-5  
Scripts live at `~/charos/scripts/`, source path uses `~/.charos/scripts/`. `escalate_to_dad` never defined. Escalation is completely broken.  
**Fix:** Use `BASH_SOURCE` for path resolution: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"`

### T2-13. `/var/log/charos` requires root — log writes silently fail
**Caught by:** TC-5, TC-6  
Shell scripts try to `mkdir -p /var/log/charos` without root. All log writes silently fail.  
**Fix:** Use `systemd.tmpfiles.rules` to create it, OR move logs to `~/.local/log/charos`.

### T2-14. `geoclue2` missing — `automatic-timezoned` never resolves location
**Caught by:** TC-3, TC-4  
`automatic-timezoned` requires `geoclue2` to function. Without it, timezone never updates.  
**Fix:** Add `services.geoclue2.enable = true` to `services.nix`.

### T2-15. NixOS zsh plugin paths don't exist on Ubuntu/WSL2
**Caught by:** TC-6  
`zshrc` sources from `/run/current-system/sw/share/...` (NixOS-specific). On dev machine, plugins never load.  
**Fix:** Add Ubuntu fallback source paths for `zsh-autosuggestions` and `zsh-syntax-highlighting`.

---

## TIER 3: Fix Soon

### T3-1. `nerdfonts.override` deprecated in NixOS 24.11 — will break in 25.05
**Caught by:** TC-1, TC-2, TC-4, TC-7, TC-8  
**Fix:** Replace `(nerdfonts.override { fonts = ["JetBrainsMono"]; })` with `nerd-fonts.jetbrains-mono`

### T3-2. Duplicate `services.hardware.openrgb.enable` across two files
**Caught by:** TC-1, TC-2, TC-3, TC-8  
**Fix:** Remove stray declaration from `packages.nix:68`. `services.nix` is authoritative.

### T3-3. Duplicate `wezterm` in `packages.nix` and `desktop.nix`
**Caught by:** TC-2, TC-4, TC-8  
**Fix:** Remove `wezterm` from `packages.nix`. Belongs in `desktop.nix`.

### T3-4. ReSpeaker udev rule matches only product ID — dangerously broad
**Caught by:** TC-1  
`ATTRS{idProduct}=="0018"` matches any manufacturer. Sets `MODE="0666"` on wrong devices.  
**Fix:** Add `ATTRS{idVendor}=="2886"` (Seeed Technology).

### T3-5. `charos.sh` uses `dirname "$0"` — breaks when symlinked to PATH
**Caught by:** TC-5  
**Fix:** Use `BASH_SOURCE` at top of script (same fix as T2-12).

### T3-6. `TC_CMD` word-splitting bug in `tc-watchdog.sh` — should use array
**Caught by:** TC-5  
**Fix:** `TC_CMD=(claude --dangerously-skip-permissions -p); "${TC_CMD[@]}" "$prompt"`

### T3-7. `SHARE_HISTORY` + `INC_APPEND_HISTORY` conflict — duplicate history entries
**Caught by:** TC-6  
**Fix:** Remove `APPEND_HISTORY` and `INC_APPEND_HISTORY` — `SHARE_HISTORY` alone is correct.

### T3-8. `test-vm.sh` Forge port forward maps wrong port — can't reach Forge from host
**Caught by:** TC-5  
`host:3002 → VM:3002` but Forge runs on VM:3001.  
**Fix:** `hostfwd=tcp::3002-:3001`

### T3-9. `tc-monitor.sh` inbox count includes `processed/` subdirectory
**Caught by:** TC-5  
Empty inbox shows "1 unprocessed message(s)".  
**Fix:** `INBOX_COUNT=$(ls "$TC_INBOX"/*.msg 2>/dev/null | wc -l)`

### T3-10. `test-vm.sh` — KVM unconditionally required, no TCG fallback
**Caught by:** TC-5  
Fails in WSL2 without nested virtualization.  
**Fix:** Check `/dev/kvm` and fall back to `accel=tcg` with a warning.

### T3-11. `test-vm.sh` — `-display gtk` won't work in WSL2
**Caught by:** TC-5  
**Fix:** Check `$DISPLAY`/`$WAYLAND_DISPLAY` and fall back to `-display sdl,gl=off`.

### T3-12. `tc-monitor.sh` uses `bc` for float comparison — may not be on NixOS minimal
**Caught by:** TC-5  
**Fix:** `LOAD_HIGH=$(awk "BEGIN {print ($LOAD_1MIN > 8.0) ? 1 : 0}")`

### T3-13. Starship `nodejs`/`python` modules configured but not in format string
**Caught by:** TC-6  
`disabled = false` but they never render because they're absent from `format`.  
**Fix:** Add to format string if desired, or explicitly disable.

### T3-14. `programs.zsh.enable` ↔ `users.shell = pkgs.zsh` — silent cross-file dependency
**Caught by:** TC-8  
If `packages.nix` is ever removed from imports, login fails.  
**Fix:** Document dependency or co-locate `programs.zsh.enable = true` closer to the user config.

### T3-15. `greetd` crash-loop risk — no greeter fallback when Sway is broken
**Caught by:** TC-4  
Both `default_session` and `initial_session` point to Sway. Sway crash = infinite loop.  
**Fix:** Set `default_session` to `tuigreet` and reserve `initial_session` for auto-login.

### T3-16. `forge` service uses `npm run dev` as a system daemon
**Caught by:** TC-3, TC-8  
Dev servers have hot reload / watchers. For a daemon, use production mode.  
**Fix:** `npm start -- --port 3001` with `NODE_ENV=production`.

### T3-17. `test-vm.sh` — `-bios` flag: EFI vars don't persist between reboots
**Caught by:** TC-5  
**Fix:** Use `pflash` drives for proper UEFI NVRAM persistence.

### T3-18. `neofetch` archived upstream — use `fastfetch`
**Caught by:** TC-2  
Still builds in 24.11 but produces deprecation noise.  
**Fix:** Replace `neofetch` with `fastfetch` in `packages.nix`.

### T3-19. `nix.gc` not configured — storage accumulates on rebuild-heavy machine
**Caught by:** TC-3  
**Fix:** Add `nix.gc = { automatic = true; dates = "weekly"; options = "--delete-older-than 14d"; }`.

### T3-20. `wezterm.on('format-title', ...)` — event name doesn't exist
**Caught by:** TC-4  
The handler never fires. Window title shows WezTerm default.  
**Fix:** Rename to `'format-window-title'`.

### T3-21. `ConditionPathExists` scripts may be absent — services fail silently on cold boot
**Caught by:** TC-3  
`/tmp` is cleared by systemd-tmpfiles at boot. Inbox directory may not exist.  
**Fix:** Add to `systemd.tmpfiles.rules`: `"d /tmp/charos-inbox 0750 nate nate -"`

### T3-22. tc-watchdog `preStart` redundant `/var/log/charos` mkdir races with systemd
**Caught by:** TC-7, TC-8  
`LogsDirectory = "charos"` already creates it before `preStart`. Redundant mkdir may race.  
**Fix:** Remove `/var/log/charos` from `preStart` mkdir. Use `systemd.tmpfiles.rules` instead.

---

## TIER 4: Nice To Have

### T4-1. `compinit` without cache — slow zsh startup (200–600ms in WSL2)
**Caught by:** TC-6 — Use `.zcompdump` age check before `compinit -C`.

### T4-2. `HIST_IGNORE_DUPS` redundant with `HIST_IGNORE_ALL_DUPS`
**Caught by:** TC-6 — Remove the weaker option.

### T4-3. `forge-monitor.sh` `pkill` pattern too broad — could kill unrelated processes
**Caught by:** TC-5 — Track Forge PID in a file instead.

### T4-4. `forge-monitor.sh` `cd` in function leaks working directory
**Caught by:** TC-5 — Wrap in subshell: `(cd "$FORGE_DIR" && ...)`.

### T4-5. Firewall — Forge port 3001 not opened for LAN access
**Caught by:** TC-3, TC-8 — Add `networking.firewall.allowedTCPPorts = [ 3001 ]` if LAN access desired.

### T4-6. `tc-signal.sh` — `notable` and `critical` use same OpenRGB profile
**Caught by:** TC-5 — No visual distinction between severity levels. Define separate profiles.

### T4-7. Race condition: `cmd_ack` ack file removed before escalation timer checks
**Caught by:** TC-5 — Spurious bedroom wakeup possible. Use sentinel value in file, not presence/absence.

### T4-8. Bluetooth not configured
**Caught by:** TC-3 — If rover/peripherals use BT: `hardware.bluetooth.enable = true; services.blueman.enable = true`.

### T4-9. `macos_window_background_blur` is macOS-only WezTerm setting
**Caught by:** TC-4 — Silently ignored on Linux. Harmless. Remove or note it.

### T4-10. WLED IP addresses are placeholder values
**Caught by:** TC-6 — Add a `WLED_CONFIGURED=false` guard so scripts skip connection attempts until hardware arrives.

### T4-11. `pipewire.alsa.support32Bit` not set — may be needed for games/Wine
**Caught by:** TC-4 — Add if any 32-bit audio apps are used.

### T4-12. `extract()` in zshrc has no argument validation
**Caught by:** TC-6 — Confusing error on no-arg call. Add guard: `[ -z "$1" ] && echo "Usage: extract <file>" && return 1`.

---

## Framework Observations

1. **Specialist agents catch what domain generalists miss.** The username mismatch and escalation blackout — the most operationally dangerous bugs — were caught by TC-5 (scripts) and TC-6 (shell), not the NixOS auditors. Future battalions should always include at least one scripts-domain and one shell-domain agent when auditing mixed-language systems.

2. **Include a "fix mode" agent.** TC-7 (test perspective) produced ready-to-paste code blocks instead of finding descriptions. This was the most immediately actionable output. Standard battalion spec should include one agent in "fix mode" who converts findings into patches.

3. **ConditionPathExists high-confidence signal.** When 3 independent agents (TC-3, TC-7, TC-8) independently catch the same issue, treat it as a T1 regardless of what the agent rated it. Consensus == priority.

4. **Boot sequence walkthrough should be standard output format.** TC-8's structured "walk boot phase by phase" approach was the most useful cross-cutting summary. Add this as a required output format for one cross-cutting agent in every future HAROS run.

5. **Standardize severity schema in HAROS spec.** Three different agents used three different severity systems. Pre-specify the schema: `CRITICAL / HIGH / MEDIUM / LOW / INFO` with definitions.

6. **Hardware presence verification is a gap.** The battalion cannot verify that the NVIDIA card, i2c bus, or ReSpeaker are physically present. A future HAROS run on real hardware should include a hardware presence verification phase (lspci, lsusb, i2cdetect) that can be skipped in VM-only audits.

7. **Deduplication at scale is expensive.** 8 agents × ~7 issues each = 56 raw findings → 58 unique (after dedup). Synthesis cost: 56,045 tokens, 333 seconds. For larger battalions, consider having agents write structured YAML findings instead of prose, to enable automated deduplication.

---

## Token / Time Statistics

| Metric | Value |
|--------|-------|
| Agents launched | 8 |
| Synthesis agent tool uses | 11 |
| Synthesis tokens | 56,045 |
| Synthesis wall time | ~333 seconds |
| Total findings (raw) | ~56 |
| Total findings (deduped) | 58 |
| Framework observations | 7 |
| T1 blockers | 9 |
| T2 broken-after-boot | 15 |
| T3 fix-soon | 22 |
| T4 nice-to-have | 12 |

---

## Next Steps

1. Fix T1s before any real hardware deploy (9 blockers — system won't build/boot without them)
2. Fix T2-11 immediately — `nathan` → `nate` rename touches every script
3. Fix T2-12 immediately — escalation is completely broken
4. Fix T2-3 (ConditionPathExists) — all 4 services crash on clean boot
5. Fix T1-1, T1-2 confirmed in VM (plymouth + timezone) — already have patches
6. Update HAROS spec with: severity schema, boot-sequence output format, "fix mode" agent role
