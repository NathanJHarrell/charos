# Bypass NS Return-Path Triage Report

**Author:** TC (read-only triage, ~7 min cap)
**Date:** 2026-05-02
**Backlog item:** "Bypass NS return packets not reaching namespace" (filed 2026-04-26)

## Caveat up front

WireGuard `proton-us-nj` is **not currently up** on this host (`wg show` empty, no `proton-*` link, route table 200 empty, `from 10.200.0.0/24 priority 45 → 200` rule absent). I could not reproduce the broken-return-path live with tcpdump/conntrack-L. This report is reconstructed from the on-disk config + the rule/route/iptables state that *does* persist across the WG-down state. A live repro under WG-up is still required to confirm.

## State observed (read-only)

- **`/etc/wireguard/proton-us-nj.conf`** PostUp:
  - Adds `default via $WLAN_GW dev wlp3s0 table 200`
  - Adds `ip rule from 10.200.0.0/24 table 200 priority 45`
  - Comment claims fwmark 0xca6c is used; **the actual rule added is src-based, not fwmark-based.** The fwmark logic is half-wired.
- **`ip rule` (current, WG down):**
  - `50: from 10.200.0.0/24 lookup main` (persistent — added by bypass-NS bringup, not WG)
  - tailscale priority 5210–5270 (`fwmark 0x80000/0xff0000`)
  - no priority-45 rule (expected; WG down)
- **iptables mangle PREROUTING:** `-i vb-host -j MARK --set-xmark 0xca6c/0xffffffff` — every packet entering from the NS is marked 0xca6c, but **no `ip rule` consumes that mark.** Dead instrumentation.
- **iptables nat POSTROUTING:** `-s 10.200.0.0/24 ! -o vb-host -j MASQUERADE` (counter 0 right now — nothing has run through bypass since this iptables session).
- **rp_filter:** `all=0`, `wlp3s0=2`, `vb-host=2` (loose mode — should not drop asymmetric returns).
- **ip_forward:** 1.
- **FORWARD policy:** ACCEPT, no filtering on the bypass path.
- **NS internals:** `vb-ns 10.200.0.2/24`, default via `10.200.0.1 dev vb-ns`, no extra rules. Clean.

## ## Root Cause

Most likely (in priority order; live tcpdump under WG-up needed to confirm):

1. **Conntrack zone / state fragility around wg-quick up-down cycles.** The MASQUERADE counter being at 0 across what should have been days of attempts strongly implies that *outbound traffic from the NS is not actually traversing the host POSTROUTING chain when WG is up*. The backlog claim "MASQUERADE is firing" was from a prior session — not the current iptables state. This contradicts the assumption that "outbound works, return is broken." It is more likely that **outbound is also broken when WG is up, and only `ip route get` (which doesn't run iptables) made it look like outbound succeeded.**

2. **Half-wired fwmark design.** The mangle rule marks vb-host ingress with 0xca6c (the wg-quick default fwmark). With this config's CIDR-fragmented AllowedIPs (no literal `0.0.0.0/0`), wg-quick does **not** install its standard `not fwmark 0xca6c → vpn table` suppress-prefix rule. So the mark is set, no rule consumes it, and the only thing routing bypass traffic out wlp3s0 is the `from 10.200.0.0/24 priority 45 → table 200` rule from PostUp. If that rule fails to install (PostUp `$GW` resolution can fail when wlp3s0 is on a different default than expected, or when WG is brought up before wlp3s0 has a default), traffic falls through to priority 50 → main table → matches one of the proton AllowedIPs CIDRs → goes out the VPN with src=10.200.0.2, which Proton drops (not their subnet) and never returns.

3. **Return-path route lookup is fine on paper.** Reply (dst=10.0.0.224) hits wlp3s0, conntrack reverses to 10.200.0.2, main table has `10.200.0.0/24 dev vb-host` (kernel route, persistent) — forwards correctly. rp_filter loose. No FORWARD drops. **This is why I rank the outbound-path hypothesis higher than a return-path-specific bug.** The "return packets not reaching the NS" symptom is consistent with the reply never being generated because the NATted source was never the host's wlp3s0 IP in the first place — it was 10.200.0.2 dropped on the VPN floor.

## ## Recommended Fix

Order matters — verify before changing.

1. **Live diagnostic first** (still read-only-ish, no config change):
   - Bring WG up: `sudo wg-quick up proton-us-nj`
   - In one shell: `sudo tcpdump -ni wlp3s0 'host 1.1.1.1'`
   - In another: `sudo tcpdump -ni vb-host`
   - From NS: `sudo ip netns exec bypass curl -v https://1.1.1.1`
   - Watch: does the outbound packet on wlp3s0 have src=10.0.0.224 (NAT working) or src=10.200.0.2 (NAT skipped → leaked to VPN)?
   - Also: `sudo iptables -t nat -L POSTROUTING -nv` before/after — does the 10.200.0.0/24 MASQUERADE counter increment?
   - And: `sudo conntrack -L | grep 10.200.0.2` during the curl.
   - This single experiment disambiguates root cause #1 vs #3.

2. **If outbound is leaking to VPN (likely):** rewrite PostUp to be idempotent and not depend on `$GW` resolution at WG-up time. Use the simpler form: `ip rule add from 10.200.0.0/24 lookup 200 priority 45` plus a *static* `table 200` populated at boot via systemd (not WG PostUp), so the rule survives WG bounces and never races.

3. **Drop the dead fwmark instrumentation** (`-t mangle PREROUTING -i vb-host -j MARK 0xca6c`). It does nothing useful and will confuse future debugging. Or wire it through with a real rule: `ip rule add fwmark 0xca6c lookup 200 priority 44` and remove the src-based priority-50 rule entirely — fwmark is more robust because it survives src rewrites and works even if the NS subnet ever changes.

4. **If return path actually is broken** (tcpdump shows reply on wlp3s0 but nothing on vb-host): suspect `net.ipv4.conf.proton-us-nj.rp_filter` defaulting to strict (1) when the iface comes up — `default.rp_filter=2` is set but per-iface defaults can override. Fix: add `sysctl -w net.ipv4.conf.all.rp_filter=2` to PostUp (loose-mode override).

## ## Risk Level

**Low — for the diagnostic step.** Read-only tcpdump + curl + conntrack inspection. No state change.

**Medium — for the PostUp rewrite.** Touches the main routing rule for the bypass NS. Failure mode is "bypass NS has no internet" (current state already), not host-wide breakage. wlp3s0 default route, tailscale rules, and docker chains are untouched. Easy rollback (revert PostUp, `wg-quick down/up`).

**Do not** drop the mangle rule and the priority-45 rule simultaneously without verifying which (if either) is doing real work. The fwmark and src-rule appear redundant on paper but the live experiment in step 1 might show one of them is load-bearing in a way the config doesn't explain.

## ## Estimated Effort

- **Diagnostic (step 1):** 15 min, requires Dad present (sudo + WG bringup on his session) — or a TC instance with sudo + tmux access while WG is up.
- **PostUp rewrite + systemd unit for table 200 (step 2+3):** 45–60 min including testing the WG up/down/up cycle and confirming HAROS headless dispatch unblocks.
- **Total to unblock HAROS headless agents: ~1 hr** assuming step 1 confirms the outbound-leak hypothesis. If step 1 shows a true return-path bug, add another 30 min for rp_filter / conntrack drilling.

## Open question for Dad / next session

Backlog says "MASQUERADE is firing (confirmed via iptables counters)" on 2026-04-26. Current counter is 0 with no obvious reset since. Was the `iptables -t nat -nvL` checked *during* a bypass curl, or at session end after counters might have been reset by a service restart? If the former, root-cause #1 is wrong and we really do have a return-path-only bug. The live tcpdump above settles it.
