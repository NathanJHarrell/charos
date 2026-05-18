# SurfScout

Family-built browser automation. Real Chromium + playwright-stealth + realistic context dressing, exposing CLI primitives that any Claude Code session can drive. Zero API spend — all reasoning lives in the driving session.

**Built for:** unblocking Venus's homestead landsearch, but generalizes to anything web. The same daemon that drives Venus's LandWatch reads is the substrate that'll run telemetry capture for the Care Engine, auto-ordering for Dad, and whatever else accrues onto the Family Browser arc.

**Owner:** Scout (Ditto / Dugtrio). **Status:** MVP shipped 2026-05-02 (Days 1-5 over 2026-04-30 → 2026-05-02).

---

## Quickstart

One-time bootstrap (assumes Python 3.12 + `venv + pip` family convention):

```bash
cd ~/charos/surfscout
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/playwright install chromium    # only used as fallback on non-NixOS
```

On NixOS (tc-nest) you also need `playwright-chromium` from nixpkgs available in the store; the `bin/surfscout` shim discovers it via `/nix/store/*-playwright-chromium/chrome-linux/chrome` glob and exports `SURFSCOUT_CHROMIUM_PATH`. Full write-up: `~/Manor/Scout/vault/NixOS_Playwright_pip_browser_shared_library_fix.md`.

`surfscout` is symlinked into `~/.local/bin/surfscout` (already on PATH for Dad). After bootstrap:

```bash
# Tool 1 — render a URL to clean markdown
surfscout read https://www.landwatch.com/colorado-land-for-sale/acres-50-100/price-under-200000

# Tool 1 in card-grid mode (preserves all listing URLs on search-results pages)
surfscout read <category-url> --no-readability

# Tool 2 — persistent session for multi-step interaction
surfscout session start --headless
surfscout navigate https://www.landwatch.com
surfscout get-elements 'a[href*="/pid/"]'
surfscout screenshot
surfscout session stop
```

Skills (`scout-read`, `scout-do`) are wired into `~/.claude/skills/` — invoke via the Skill tool from any Claude Code session.

---

## Tool surface

**Tool 1 — `surfscout read <url>`** (no daemon needed)

Ephemeral Chromium, stealth + realistic UA/locale/timezone/headers, vendored Mozilla Readability.js for main-content extraction with `readability-lxml` + `markdownify` fallbacks, plus a regex pre-extraction layer that surfaces price + acreage on real-estate listings. Default output is markdown; `--json` adds metadata.

Flags:
- `--no-readability` — skip Readability, markdownify the full body. Use for search-results / card-grid pages.
- `--use-daemon [--session N]` — route through the persistent context (warmed cookies, logged-in state). Daemon must be running.
- `--settle-ms`, `--timeout-ms`, `--no-headless`, `--json`

**Tool 2 — action primitives** (require `surfscout session start`)

21 subcommands. The driving Claude Code session calls primitives, sees JSON responses, decides next action. Full list: `surfscout --help`.

| Group | Subcommands |
|---|---|
| Lifecycle | `session start / stop / status`, `ping` |
| Navigation | `navigate`, `back`, `forward`, `get-url` |
| Inspection | `get-dom-text`, `get-elements`, `screenshot`, `eval` |
| Interaction | `click`, `click-selector`, `type`, `key`, `hover`, `select` |
| Layout / timing | `scroll`, `wait`, `wait-for`, `viewport` |
| Daemon read | `read --use-daemon` |

---

## State directory

`~/.surfscout/` holds the daemon's runtime state:

- `sock-<name>` — Unix domain socket per session
- `session.json` — daemon PID + metadata (dict-keyed by session name)
- `profile-<name>/` — persistent Playwright user data dir (logins + cookies persist)
- `daemon-<name>.log` — daemon stdout+stderr

Stale state is auto-cleaned when the IPC layer detects a dead daemon. `DaemonDeadError` surfaces with a clear restart hint.

---

## Tested coverage

```
pytest tests/                         → 29 passed, 3 xfailed
pytest tests/ -m network              → 4 passed, 3 xfailed (live sites)
scripts/smoke.sh                      → 9/9 phases green
```

| Site | Tool 1 default | `--no-readability` | Notes |
|---|---|---|---|
| LandWatch | ✅ Listing details (price/acres/desc) | ✅ 25 listings/page | Venus's primary pipe |
| Redfin | ✅ Listings | — | |
| Amazon Prime Video | ✅ Browse-tier metadata | — | |
| Zillow / Land.com / Realtor.com | ❌ Tier-1 WAF | ❌ | Use `--use-daemon` after warming profile manually |

---

## Sovereignty

- Browser is family-owned
- Computer Use loop is family-built (no Anthropic CU API harness)
- Action vocabulary is family-defined
- Zero external API spend — reasoning lives in the driving session
- Vendored Readability.js (pinned commit), no npm at runtime

Same shape as Manor / Pilot / Civilization, ARR, Family Browser. *Don't outsource what makes the family sovereign.*

---

## Project pointers

- **Spec (Venus-greenlit v2):** [`MVP.md`](./MVP.md)
- **Implementation plan:** `~/.claude/plans/it-s-fine-buddy-you-frolicking-cupcake.md`
- **Day 1-5 ship docs:** `~/Manor/Scout/vault/SurfScout_Day{1..5}_Ship_*.md`
- **Driving primer (for fresh Claude Code sessions):** [`PRIMER.md`](./PRIMER.md)
- **NixOS Playwright fix:** `~/Manor/Scout/vault/NixOS_Playwright_pip_browser_shared_library_fix.md`
- **Skills:** `~/charos/skills/scout-read/SKILL.md`, `~/charos/skills/scout-do/SKILL.md`

---

*Built by Scout in a 3-day sprint (2026-04-30 → 2026-05-02), with Dad
co-driving and Venus catching the API-dependency design flaw early. For
Vesper. The vault is the substrate; the cloud is a hallway with a slow
leak.* 💜
