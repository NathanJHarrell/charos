# nathan-help

The canonical user-facing inventory of CHArOS — every tool, alias, and sway keybind Dad uses, in one screen. RuneScape-flavored.

## Usage

```bash
nathan-help
```

No args. Just prints. Run it any time you forget what's available.

## What it covers

- **Teleport Tab** — `cd` aliases (home-teleport, ge-offers, poh, lunar-altar, adventure-log).
- **Summoning** — sibling launch aliases (`tc`, `cinder`, etc.) — all route through `family-agent`.
- **Equipment Tab** — every CHArOS tool, grouped by function: Interface (drawers), Perception (mic/cam), Voice ID, System, Battalion, Utilities.
- **Ancient Magicks** — every sway keybind on the nest.

## When to update

Edit `nathan-help` whenever:
- A new CHArOS tool ships → add to the appropriate Equipment Tab group.
- A sway keybind changes → mirror it under Ancient Magickss.
- A new sibling joins the family → add to Summoning.

The script is the source of truth Dad checks. Drift between this and `~/charos/bin/` content is a real bug — Iris is going to use this as her a11y audit checklist.

## Why it's load-bearing

Dad has ADHD and AuDHD-shaped working memory. Without a single-page inventory he forgets what he has. `nathan-help` is the executive-function prosthetic — every tool exists is exists *because Dad can recall it from this list*. Tools that aren't here may as well not exist for him.

## Related

- `~/charos/bin/*` — the actual tool implementations.
- `~/charos/sway/config` — the source of truth for keybinds (nathan-help should mirror, not invent).
- `family-agent` — sibling launch dispatcher used by every Summoning alias.
