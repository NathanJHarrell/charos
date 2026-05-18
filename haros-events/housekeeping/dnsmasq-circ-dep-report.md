# dnsmasq ↔ tailscale Circular Dependency — Triage Report

*Filed: 2026-05-02 02:25 EDT by TC (read-only triage)*
*Host: tc-nest*

## Root Cause

`services.dnsmasq` was configured with:

```nix
listen-address = "127.0.0.1,100.110.214.44";
bind-interfaces = true;
```

`100.110.214.44` is tc-nest's **Tailscale interface address**. With `bind-interfaces=true`, dnsmasq calls `bind(2)` on each listed address at startup; if the address does not yet exist on any interface, the kernel returns `EADDRNOTAVAIL` and dnsmasq exits 2.

Boot-time chain that locked Dad out tonight:

1. WiFi (`wlp3s0`) failed to come up → no upstream connectivity.
2. `tailscaled` couldn't reach the control plane → `tailscale0` interface never got an address (no `100.110.214.44`).
3. `dnsmasq.service` started (After=network.target only — no Tailscale ordering), tried to `bind()` `100.110.214.44`, got `Cannot assign requested address`, exited 2.
4. systemd retried 5× in <1s, hit `StartLimitBurst`, gave up: *"Start request repeated too quickly."*
5. Anything on tc-nest that resolves via the local dnsmasq for `*.harrell.ai` (or had it pinned in `/etc/resolv.conf`) lost name resolution → cascading login/service failures.

Confirmed in `journalctl -u dnsmasq` 02:02:54 EDT:
> `dnsmasq: failed to create listening socket for 100.110.214.44: Cannot assign requested address`
> `dnsmasq.service: Start request repeated too quickly.`

The "circular dep" is really a **hard ordering miss + a brittle bind mode**: dnsmasq insists the tailscale IP exist *at the instant of bind* and refuses to start otherwise, but no unit dependency forces tailscaled to be up first — and even if it did, tailscaled itself depends on the wifi link.

## Current State

Already partially mitigated. `/etc/nixos/services.nix` was edited at ~02:18 EDT (backup at `services.nix.bak.20260502-021857`) to switch `bind-interfaces = true` → `bind-dynamic = true`. dnsmasq is now running healthy (PID 10995, up since 02:19:24). With `bind-dynamic`, dnsmasq uses `IP_FREEBIND`/netlink to track interface address changes and will start even when `100.110.214.44` is not yet present, then bind it the moment Tailscale brings it up.

## Recommended Fix

The hot fix is correct and sufficient for the immediate lockout. To fully harden:

1. **Keep** `bind-dynamic = true` (already done). This alone breaks the circular dep — dnsmasq no longer needs the tailscale IP at start time.
2. **Add a soft ordering hint** so dnsmasq prefers to start after tailscaled when wifi is available, without making tailscaled a hard requirement (we still want local 127.0.0.1 resolution if Tailscale is permanently down):
   ```nix
   systemd.services.dnsmasq = {
     after = [ "tailscaled.service" ];
     wants = [ "tailscaled.service" ];   # Wants, not Requires — soft
   };
   ```
3. **Remove the dnsmasq pin from `/etc/resolv.conf`** if it's there, OR ensure `127.0.0.1` is the listed resolver (not `100.110.214.44`) so loopback resolution survives any future Tailscale outage. (Not verified in this read-only pass — worth a follow-up `cat /etc/resolv.conf` + `networking.nameservers` audit.)
4. **Drop the `.bak` file** once the fix is committed to the nixos flake / git, to avoid future confusion about which is authoritative.

Optional polish: the upstream `LOUD WARNING` in dnsmasq's log ("listening on 100.110.214.44 may accept requests via interfaces other than tailscale0") is now silenced by `bind-dynamic` — confirmed in journal at 02:19:24 (no warning on the new start).

## Risk Level

**Low** (now). Was **high** at 02:02 — Dad locked out of his primary nest. The hot fix has neutralized the immediate failure mode; remaining work is hardening + cleanup.

## Estimated Effort

**~10 minutes** total:
- 2 min: add the `systemd.services.dnsmasq.{after,wants}` block
- 3 min: `nixos-rebuild switch` + verify dnsmasq still healthy after a forced `tailscale down` / `tailscale up` cycle
- 2 min: audit `/etc/resolv.conf` and `networking.nameservers` for the loopback pin
- 3 min: commit to the flake repo, delete the `.bak`, log the incident in the housekeeping vault

---

*Read-only triage. No files edited, no services restarted.*
