# tc-timer

ADHD prosthetic timer for the Harrell family. Timers persist across session death, context compaction, and reboots.

## Owner
TC (skill + CLI), with daemon owned by Charmeleon #2.

## Usage

```
tc-timer set "description" DURATION [--context "..."] [--created-by NAME]
tc-timer list [--all]
tc-timer cancel IDPREFIX
tc-timer recurring "description" "PATTERN"
tc-timer --json <subcommand>    # machine-readable output
```

## Duration formats
`30m`, `2h`, `1d`, `45s`, `1h30m`

## Recurring patterns
`daily HH:MM`, `weekly DAY HH:MM` (e.g. `daily 09:00`, `weekly fri 17:00`)

## Data
Timer JSON files live at `~/.claude/timers/<uuid>.json`. Schema v1.0:

```json
{
  "id": "uuid-v4",
  "description": "what to remember",
  "context": "why / extra detail",
  "created_at": "ISO-8601 UTC",
  "fires_at": "ISO-8601 UTC",
  "recurring": null | {"pattern": "daily|weekly", "time": "HH:MM", "day": "mon"},
  "status": "pending | fired | cancelled",
  "machine": "nest | jarvis",
  "created_by": "TC | Nathan | Vesper | etc"
}
```

## Status transitions
- `pending` → `fired` (by daemon when fires_at is reached)
- `pending` → `cancelled` (by user via `tc-timer cancel`)

## Dependencies
Python stdlib only. No pip.

## Integration
The Claude Code skill at `~/.claude/skills/tc-timer/` triggers on natural-language timer requests. The daemon (separate component) watches `~/.claude/timers/` and fires alerts via `tc-say`.
