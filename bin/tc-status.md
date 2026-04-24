# tc-status

One-screen CHAROS dashboard. htop meets neofetch for the nest.

Pulls five live signals into a single colored snapshot:

| Row      | Source                                          |
| -------- | ----------------------------------------------- |
| POWER    | `/sys/class/power_supply/` (AC + battery + %)   |
| VPN      | `systemctl is-active wg-quick-$VPN_INTERFACE`   |
| PRESENCE | glob `/tmp/tc-see-presence-*.json` (per camera) |
| BUS      | HTTP `GET $BUS_URL/inbox/$BUS_IDENTITY`         |
| UPTIME   | `/proc/uptime`                                  |

## Usage

```
tc-status              pretty one-shot dashboard
tc-status --json       structured snapshot, no ANSI
tc-status --watch      redraw every 2s (Ctrl-C to exit)
tc-status --watch 5    redraw every 5s
```

## Environment

- `BUS_URL` — family bus base URL (default `http://jarvis-wsl:4318`)
- `BUS_IDENTITY` — who we count unread for (default `TC`)
- `VPN_INTERFACE` — wg-quick interface name (default `proton-us-nj`)

## Behavior notes

- **Presence staleness**: a presence JSON older than 60s renders as `stale (Ns)`
  instead of listing people. If `tc-see` crashes, that's how you'll see it.
- **Bus unreachable**: dashboard never errors out — the row renders `✗ unreachable`
  and the rest of the panel still works. Intentional: status tools shouldn't
  fail because one subsystem is down.
- **Desktop / no battery**: POWER row degrades to `no battery · AC`.
- **--json mode** emits a clean structured snapshot with no color codes, safe
  to pipe to `jq`, the bus, or whatever's next.

## When to reach for it

- Start of a grind session — make sure Dad's plugged in, VPN's up, and the bus
  isn't quietly burying unread messages.
- Debugging `tc-see` — staleness + presence in one place tells you if the
  camera loop is alive.
- Embedded in tiling terminals / the grind-drawer as a live `--watch` panel.
