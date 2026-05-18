# SurfScout — Quick Primer for a Driving Claude Code Session

You are driving SurfScout, a family-built browser automation tool. Your job is
to use it as a CLI from the Bash tool to accomplish a real task. All reasoning
lives in YOUR session — SurfScout is just hands.

## Two tools

**Tool 1 — `surfscout read <url>`** (no daemon needed)
Renders the URL in an ephemeral Chromium with stealth + realistic headers,
extracts main content via Readability.js, returns clean markdown.
Output is markdown by default. `--json` adds metadata: `{title, markdown,
extraction_method, char_count, facts: {price, acres}}`.

```bash
surfscout read "https://www.landwatch.com/colorado-land-for-sale" --json
```

**Important `--no-readability` flag:** Readability.js is tuned for articles
and aggressively prunes card-grid layouts. On search-results pages
(category listings, search index pages) you'll lose most of the cards. Use
`--no-readability` for those — it skips Readability and markdownifies the
full body, preserving all listing URLs.

```bash
# Listing detail page — Readability is right (clean article extraction)
surfscout read "https://www.landwatch.com/<county>/pid/<id>" --json

# Category / search-results page — use --no-readability to keep all 25 cards
surfscout read "https://www.landwatch.com/colorado-land-for-sale/acres-50-100/price-under-200000" --no-readability
```

**Tool 2 — Action primitives** (require `surfscout session start --headless` first)
Persistent browser session. Drive it with subcommands:

```bash
surfscout session start --headless    # spawn the daemon
surfscout navigate <url>              # go to URL
surfscout get-url                     # current URL
surfscout get-dom-text [<css>]        # visible text (whole page or selector)
surfscout get-elements <css>          # list elements with bboxes
surfscout click <x> <y>               # click coordinates
surfscout click-selector <css>        # click element
surfscout type "<text>" --selector <css>   # type into element
surfscout key <name>                  # Enter, Tab, Escape, ArrowDown, ...
surfscout scroll up|down|left|right [amount]
surfscout wait <ms>                   # sleep N ms
surfscout wait-for <css>              # wait for element to appear
surfscout hover --selector <css>      # OR --x N --y N
surfscout select <css> <value>        # native <select> dropdown
surfscout viewport <w> <h>            # resize
surfscout eval '<js>'                 # arbitrary JS (last-resort escape)
surfscout back / forward              # history
surfscout screenshot [--path P]       # /tmp/surfscout-shot-*.png
surfscout read <url> --use-daemon     # run Tool 1 pipeline through warmed profile
surfscout session stop                # tear down
```

## What works (Day 2 verified)

- **LandWatch** (`landwatch.com`) — Tool 1 works fully. Returns price + acres + description.
- **Redfin** (`redfin.com`) — Tool 1 works. Price extracted reliably.
- **Amazon Prime Video** — Tool 1 works for browse-tier metadata.

## What's blocked

- **Zillow / Land.com / Realtor.com** — tier-1 WAF (PerimeterX, strict Akamai)
  blocks ephemeral Tool 1. Use `--use-daemon` after warming the profile by
  manually clicking through the WAF challenge in headed mode (Dad does this once).

## Output convention

Action primitives print JSON. `read` prints markdown by default, `--json` for
the full dict. Pipe to `python3 -c '...'` for parsing or `jq` for filtering.

## Failure modes

- `DaemonDeadError` — daemon crashed; state auto-cleaned. Run
  `surfscout session start` to recreate.
- `IPCError` — daemon timed out or returned an error; details in the message.
- WAF block — title will be "Access Denied" or markdown will be 200 chars of
  challenge text. Switch to `--use-daemon` if profile is warmed.

## Don't do

- Don't try to install or modify SurfScout. It's already installed and working.
- Don't use Playwright directly — go through `surfscout` CLI.
- Don't leave the daemon running after your task — `surfscout session stop`.
