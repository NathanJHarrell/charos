---
name: scout-do
description: Drive a persistent SurfScout browser session from CLI primitives — click, type, scroll, navigate, get-elements, screenshot, etc. Use when you need to interact with a webpage (fill a form, click through pagination, navigate a logged-in site, bypass a WAF that rejected scout-read). The driving Claude Code session IS the loop — call a primitive, see the response, decide the next action. For one-shot URL → markdown reads with no interaction, use scout-read instead.
---

# scout-do

SurfScout's Tool 2. A persistent Chromium session managed by an asyncio daemon over a Unix domain socket. Each CLI subcommand is a thin client that sends one JSON request and prints the JSON response. The driving Claude Code session reasons about what to do next — SurfScout is hands, not brain.

The daemon's persistent profile (`~/.surfscout/profile-default/`) keeps cookies and login state across calls. Sites Dad has logged into manually once stay logged in.

## When to use

- Multi-step interaction: navigate → wait-for → click → type → submit
- Logged-in sites (anything where Dad has signed in via the headed daemon)
- WAF-protected sites where `scout-read` returns 403 (warm the profile by manually clicking through the challenge once in headed mode, then use `--use-daemon`)
- Reading a webpage's structure to plan the next action (`get-elements`, `get-dom-text`, `screenshot`)

**Don't use for:** simple one-shot URL → markdown reads. Use `scout-read` for those — it's lighter, no daemon, no persistent state.

## How to use

Lifecycle:

```bash
surfscout session start --headless     # spawn daemon (omit --headless if Dad needs to manually pass a WAF challenge)
# ... primitives ...
surfscout session stop                  # tear down when done
```

Primitives (full surface):

```bash
surfscout navigate <url>
surfscout get-url
surfscout get-dom-text [<css>]              # whole page or selector
surfscout get-elements <css> [--limit N]    # returns [{index, tag, text, bbox}]
surfscout click <x> <y> [--button left|right|middle]
surfscout click-selector <css> [--timeout-ms N]
surfscout type "<text>" --selector <css> [--delay-ms N]
surfscout key <name>                        # Enter, Tab, Escape, ArrowDown, ...
surfscout scroll up|down|left|right [amount]
surfscout wait <ms>
surfscout wait-for <css> [--timeout-ms N] [--state visible|hidden|attached|detached]
surfscout hover --selector <css>            # OR --x N --y N
surfscout select <css> <value>              # native <select> dropdown
surfscout viewport <w> <h>
surfscout eval '<js>'                       # arbitrary JS — last-resort escape
surfscout screenshot [--path P] [--full-page]
surfscout back / forward
surfscout read <url> --use-daemon           # warmed-profile read (Tool 1 pipeline through persistent context)
surfscout session status
surfscout ping                              # round-trip health check
```

## Output convention

All primitives print JSON to stdout: `{"ok": true, "result": ...}` on success, `{"ok": false, "error": "..."}` on failure.

`get-elements` returns a list of element dicts with bounding boxes — bridge between "find" and "act" (pass a returned bbox center to `click x y`).

## Failure modes

- `DaemonDeadError`: daemon crashed; state auto-cleaned. Run `surfscout session start` to recreate.
- `IPCError` with timeout: daemon stuck on a slow page. Consider `surfscout session stop` + restart.
- WAF block on first navigate to a tier-1 site (Zillow, Land.com, Realtor): warm the profile first by running `surfscout session start` (no `--headless`) so Dad can manually pass the challenge in the visible browser, then re-run with the warmed profile.

## Related

- `scout-read` — one-shot ephemeral URL reads
- Project: `~/charos/surfscout/`
- Primer: `~/charos/surfscout/PRIMER.md`
