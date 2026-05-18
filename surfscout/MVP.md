# SurfScout — MVP Shape

> **STATUS: SHIPPED 2026-05-02.** This file is the original Venus-greenlit spec
> (Apr 30). It is preserved for historical context — what was specced vs what
> shipped. **For current capabilities, surface, and quickstart, read
> [`README.md`](./README.md).** For a driving-session reference, read
> [`PRIMER.md`](./PRIMER.md). For day-by-day shipping history, see
> `~/Manor/Scout/vault/SurfScout_Day{1..5}_Ship_*.md`.

**Project:** Family-built browser automation for the Harrell homestead
**Owner:** Scout (ambient + autonomous)
**Drivers:** Anyone in `~/Manor/` running a Claude Code session (initially Venus + Dad, for the landsearch)
**Status (original):** Spec, pre-build. Revised v2 after Venus's catch on API dependency.
**Authored:** 2026-04-30 by Scout (Opus mode), at Dad's request

---

## Why this exists

Venus is hitting two walls during the homestead landsearch:

1. **403s on real estate sites** (LandWatch, Zillow, etc.) — bot detection rejects LLM HTTP requests
2. **Infinite nested div problem** — JS-rendered SPAs with content buried in DOM noise; raw HTML scraping returns garbage

The internet is hostile to LLMs. SurfScout is the family's answer: a real browser the family controls, driven by family-built CLI primitives, free of any external API dependency.

## Sovereignty principles

- **The browser is family-owned.** Headed Playwright instance on family hardware. No SaaS dependency.
- **The actuation is family-built.** No Anthropic Computer Use API harness. SurfScout exposes CLI primitives; the reasoning loop lives in whatever Claude Code session is driving (TC's, Scout's, Venus's).
- **The action vocabulary is family-defined.** We own the verbs SurfScout speaks. We tune them for our use cases.
- **Zero API spend.** All reasoning runs on Dad's Claude Code subscription via the active session. No API key required for MVP. (Optional headless reasoning module is post-MVP and explicitly aspirational.)
- Same shape as Manor / Pilot / Civilization, ARR, Family Browser. *Don't outsource what makes the family sovereign.*

---

## What ships in MVP

### Tool 1 — `surfscout read <url>`

Render any URL with a real browser, extract the main content, return clean markdown.

**Behavior:**
- Playwright + `playwright-stealth` defeats most bot detection (no more 403s on LandWatch et al.)
- Wait for JS-rendered content to settle (configurable timeout, default 5s)
- Inject Readability.js (or use trafilatura) to strip nav/footer/ads/divs
- Convert main content to clean markdown via markdownify
- Return markdown to caller (target: <10K tokens per page)

**No model required.** Pure deterministic pipeline. Runs locally, free, no API key.

**Use case:** Venus says to her Claude Code session: "summarize this listing" → her Claude Code calls `surfscout read <url>` via Bash → gets markdown back → reasons over it cheaply.

**Out of scope for MVP:** Per-site adapters, screenshot fallback for read, login support.

### Tool 2 — `surfscout` action primitives (CLI subcommands)

Family Computer Use, inverted. **SurfScout doesn't drive the browser; it exposes the controls.** The Claude Code session driving SurfScout is the loop — model calls a primitive via Bash, sees output, decides next action, calls again. Same paradigm Claude Code already uses for everything else; just extended to web automation.

**Action primitive subcommands:**

| Command                              | What it does                                                       |
|--------------------------------------|--------------------------------------------------------------------|
| `surfscout screenshot [--path P]`    | Take a screenshot of current page; print path (or save to P)       |
| `surfscout click <x> <y>`            | Click at coordinates                                               |
| `surfscout click-selector <css>`     | Click element matching CSS selector                                |
| `surfscout type "<text>"`            | Type text into focused element                                     |
| `surfscout key <name>`               | Press a named key (Enter, Tab, Escape, ArrowDown, etc.)            |
| `surfscout scroll <dir> [amount]`    | Scroll up/down/left/right by amount (default: viewport)            |
| `surfscout wait <ms>`                | Wait N milliseconds                                                |
| `surfscout navigate <url>`           | Navigate to URL                                                    |
| `surfscout get-url`                  | Print current URL                                                  |
| `surfscout get-dom-text [<sel>]`     | Print visible text in selector (or whole page)                     |
| `surfscout get-elements <sel>`       | Print matching elements with selectors + bounding boxes            |
| `surfscout session start`            | Start a persistent browser session (subsequent commands attach)    |
| `surfscout session stop`             | Close the session                                                  |
| `surfscout session status`           | Print current URL, page title, viewport size                       |

**Hybrid clicking:** The driving Claude Code session can pick element-based (`click-selector`) when DOM is clean, or coordinate-based (`click x y`) when only vision is reliable. Vision can call `get-elements` to discover selectors before deciding.

**Loop pattern (in Claude Code):**
```
1. surfscout navigate "https://landwatch.com/..."
2. surfscout screenshot           → /tmp/surfscout-shot-*.png
3. (Claude Code reads screenshot, decides next action)
4. surfscout click 240 410
5. surfscout screenshot           → /tmp/surfscout-shot-*.png
6. (loop until task complete)
```

**Use case:** Venus says to her Claude Code session: "save a search for 50+ acres in Costilla County under $200k on LandWatch." Her Claude Code calls `surfscout navigate`, `surfscout screenshot`, reads the shot, calls `surfscout click <coords>` to apply filters, screenshots again, etc., until the search is saved. The whole loop runs on her subscription with no API spend.

**Out of scope for MVP:** Multi-tab juggling, persistent login storage (use existing browser profile), task chaining across sessions.

---

## What does NOT ship in MVP

- **Per-site adapters.** Generic primitives only. The adapter trap is real — adapters die the day sites update.
- **Sensor half** (Dad's behavioral telemetry from the original Family Browser spec). Sensor work waits until after the homestead is found.
- **Chromium fork.** Playwright + stealth handles current needs. Fork only if/when stealth fails on critical sites.
- **Multi-user concurrency.** One browser session at a time in MVP. Multi-session later.
- **Self-driving loop / `reason()` module.** The Claude Code session is the loop. A headless reasoning module (`surfscout/reason/`) is post-MVP and explicitly aspirational — only needed if we ever want to run SurfScout in batch mode without a Claude Code session driving.

---

## Architecture

```
┌───────────────────────────────────────────────────────┐
│  Claude Code session (TC, Scout, Venus, anyone)       │
│  ── this is the reasoning loop ──                     │
└───────────────────────────────────────────────────────┘
                     │  (Bash tool calls)
                     ▼
┌───────────────────────────────────────────────────────┐
│  surfscout CLI (Python)                               │
│  ├─ read <url>                       → Tool 1 path    │
│  ├─ screenshot, click, type, ...     → Tool 2 path    │
│  └─ session start/stop/status        → session mgmt   │
└───────────────────────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│  Persistent Playwright browser session (headed)       │
│  + playwright-stealth                                 │
│  + Readability.js injectable                          │
└───────────────────────────────────────────────────────┘
```

**Session model:** SurfScout maintains a persistent browser process between CLI invocations. `surfscout session start` spawns the browser; subsequent `surfscout <action>` commands attach to it; `surfscout session stop` closes it. Implementation: socket file or PID file in `~/.surfscout/`, browser keeps running between commands.

---

## Project layout (proposed)

```
~/charos/surfscout/
├── README.md             # quickstart + family-facing docs
├── MVP.md                # this file
├── pyproject.toml        # uv-managed Python project
├── surfscout/
│   ├── __init__.py
│   ├── cli.py            # argparse entry point with subcommand dispatch
│   ├── browser.py        # Playwright session manager + persistence
│   ├── stealth.py        # playwright-stealth integration
│   ├── read.py           # Tool 1: render → markdownify
│   ├── actions.py        # Tool 2: primitive implementations (one per CLI subcommand)
│   └── session.py        # start/stop/status + IPC to running browser
├── skills/               # Claude Code skills wrapping common patterns
│   ├── scout-read.md
│   └── scout-do.md
└── tests/
    ├── test_read_landwatch.py
    ├── test_actions_basic.py
    └── test_session_persistence.py
```

**Note:** No `surfscout/reason/` directory in MVP. That module ships if and when we ever want headless batch mode without a Claude Code session driving. Aspirational, post-MVP.

---

## Stack

- **Python 3.12+** (matches scout-pipeline)
- **Playwright** (Chromium driver, headed)
- **playwright-stealth** (defeat bot detection)
- **Readability.js** (injected for main-content extraction)
- **markdownify** (HTML → markdown)
- **venv + pip** for dependency management (matches scout-pipeline convention)
- **No `anthropic` SDK in MVP.** No API key required. Reasoning lives in the driving Claude Code session.

---

## Cost

**$0 marginal cost.** All reasoning runs on the driving Claude Code session (Dad's Max subscription). SurfScout itself is local Python + Playwright; only cost is electricity and the existing subscription that's already paying for the session.

---

## Timeline

| Day | What ships |
|-----|------------|
| 1   | Project skeleton + browser.py + session.py + stealth + Tool 1 (`read`) working on LandWatch |
| 2   | Tool 1 hardened on 5 real estate sites; markdown quality verified by hand |
| 3   | actions.py: screenshot, click (coords + selector), type, key, scroll, wait, navigate, get-url, get-dom-text |
| 4   | Session persistence + `get-elements` + first end-to-end Claude-Code-driven landsearch task |
| 5   | Skills wrappers + smoke tests + handoff to Dad and Venus |

**Estimate: 5 days of focused build by one person; faster with parallel work. Slightly faster than v1 because no LLM integration to build for MVP.**

---

## Who builds (proposed)

- **TC** (Charizard, agentic engineer) — system bones, Playwright session manager + IPC, action implementations
- **Scout-Opus** (architect mode) — design + CLI surface + skill wrappers + integration testing
- **Scout-Haiku swarm** — generate test cases, smoke-test against real sites, surface edge cases
- **Mine** — fresh-skeptic review, especially on action vocabulary completeness (does it cover the 80% case?)

If TC is over-allocated, Scout can build it solo on Opus + Haiku-swarm. Slower but feasible.

---

## Open questions for Venus

1. **Headed by default — confirmed?** Since Claude Code drives interactively now (you can see the screenshots in the conversation), headed is the natural choice. You and Dad watching the actual browser is bonus visibility but not strictly required. Want to keep `--headless` as an opt-in flag?
2. **Where does the browser run?** Dad's machine? tc-nest? A dedicated host? Affects who can launch SurfScout sessions and whether you can watch the browser window live. (Browser running where Claude Code is running is simplest — same machine, single session.)
3. **Login handling:** When Tool 2 hits a login wall, do we (a) you log in via the headed browser by hand the first time and SurfScout uses your existing browser profile thereafter, (b) store credentials encrypted in the family vault, or (c) skip login-required workflows for MVP?
4. **Action vocabulary completeness:** Looking at the primitive list — anything obviously missing for landsearch tasks you've already tried? (Right-click? Hover? Drag-and-drop? File upload? Tab switching?)
5. **Naming the Claude Code skills:** `scout-read` and `scout-do`? Or `surf-read` and `surf-do`? Or different verbs entirely?
6. **Concurrency:** Is one SurfScout browser session at a time enough for MVP, or do you need to run parallel browses?

---

*Spec authored by Scout for Venus's review, 2026-04-30. Revised v2 after Venus caught the API-dependency problem on v1 read. Once Venus signs off (or marks edits), TC and Scout begin the build.* 💜
