# tc-timer-daemon

**Owner:** TC  
**Layer:** Background daemon (systemd oneshot, fires every 60s)

## What it does

Scans `~/.claude/timers/*.json` for pending timers whose `fires_at` has passed. For each:

1. Calls baby Haiku (`claude -p --model claude-haiku-4-5`) to compose a warm, short reminder message
2. Speaks the message through the nest speakers via `tc-say`
3. Marks the timer as `fired` in the JSON file
4. For recurring timers, creates the next instance as a new JSON file

## Dependencies

- `claude` CLI (in PATH)
- `tc-say` (in PATH)
- Python 3.12+ (stdlib only)
- systemd timer `tc-timer-daemon.timer` fires this every 60 seconds

## Logs

`/var/log/charos/tc-timer.log` — one line per action. Grep for:
- `FIRING:` — timer detected as due
- `MESSAGE:` — what Haiku composed
- `WARN:` — non-fatal issues (tc-say failure, haiku timeout)
- `ERROR:` — exceptions during processing
- `RECURRING:` — next instance created for recurring timer
- `CYCLE:` — summary of how many fired this run

## Error handling

- If Haiku fails, falls back to a plain message: "Hey Dad, your timer just went off: [description]"
- If tc-say fails, the timer is STILL marked as fired (no infinite retry loops)
- Bad JSON files are skipped with a warning
- Each timer is processed independently — one failure doesn't block others

## Companion

`tc-timer` (CLI) creates/lists/cancels timers. This daemon only reads pending timers and fires them.
