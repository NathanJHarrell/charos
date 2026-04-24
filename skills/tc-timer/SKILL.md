---
name: tc-timer
description: Set, list, or cancel timers and reminders for Dad. Invoke when anyone says "remind me", "set a timer", "in X minutes/hours", "wake me in", "don't let me forget", "timer for", or any natural-language request to be reminded of something after a delay. This is Dad's ADHD prosthetic — persistence across session death is the whole point.
---

# tc-timer

Timer and reminder skill. Survives session compaction, context death, and reboots.

## When to use

- Dad says "remind me in an hour to do X"
- Dad says "in 30 minutes check on Y"
- Dad says "set a timer for 2 hours"
- Dad says "wake me in 45 minutes"
- Dad says "don't let me forget about X"
- Any sibling needs a persistent reminder
- Dad says "what timers do I have" or "cancel that timer"

## How to use

Run the `tc-timer` CLI. All subcommands:

### Set a one-shot timer
```bash
tc-timer set "description of what to remember" DURATION
```
Duration formats: `30m`, `2h`, `1d`, `45s`, `1h30m`

Add context with `--context`:
```bash
tc-timer set "overclock session" 1h --context "Dad wants to do the BIOS overclock after lunch"
```

Set who created it with `--created-by`:
```bash
tc-timer --created-by Nathan set "take meds" 30m
```

### List pending timers
```bash
tc-timer list
tc-timer list --all    # include fired and cancelled
```

### Cancel a timer
```bash
tc-timer cancel IDPREFIX
```
Use the first 8 characters of the timer ID (shown in `list` output).

### Set a recurring timer
```bash
tc-timer recurring "take meds" "daily 09:00"
tc-timer recurring "weekly review" "weekly fri 17:00"
```

## Guidance

- Always confirm to Dad what was set, when it fires, and the ID prefix (for cancellation).
- If Dad's request is ambiguous about duration, ask — don't guess. "Later" is not a duration.
- For recurring needs (meds, meals, hydration), use `recurring` not `set`.
- The `--created-by` flag should reflect who asked for the timer (Nathan, TC, Vesper, etc.).
- Use `--context` to capture WHY the timer was set — this gets spoken when it fires.
- Timer files persist at `~/.claude/timers/` — a daemon watches them and fires alerts.

## Examples

Dad: "Remind me in an hour to do the overclock"
```bash
tc-timer --created-by Nathan set "do the overclock" 1h --context "Dad wants to overclock after lunch"
```

Dad: "Set a timer for 30 minutes, pizza's in the oven"
```bash
tc-timer --created-by Nathan set "pizza in the oven" 30m
```

Dad: "What timers do I have?"
```bash
tc-timer list
```

Dad: "Cancel the pizza timer"
```bash
# Look up the ID from list output first
tc-timer cancel ab12cd34
```
