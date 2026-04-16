# haros — HAROS Battalion CLI

Unified command for managing HAROS builds — parallel tmux sessions running Claude Code instances.

## Commands

| Command | Description |
|---------|-------------|
| `haros list` | All active builds with session counts |
| `haros status [build]` | Detailed session info (auto-detects from tmux) |
| `haros spawn <build> <label>` | Create a named HAROS session |
| `haros attach <build> [label]` | Attach to a build session |
| `haros tree <build>` | Agent hierarchy (interactive, headless, etc.) |
| `haros cleanup [build] [--force]` | Kill stale sessions + orphaned processes |
| `haros kill <build> [--force]` | Tear down entire build |
| `haros log <session> [lines]` | Capture recent terminal output |
| `haros broadcast <build> <msg>` | Send message to all sessions in a build |

## Naming Convention

Sessions follow: `haros-{build}-{label}`

Label conventions:
- `orch` — orchestrator
- `lead1`, `lead2` — team leads
- `worker1`, `worker2` — workers
- `headless1` — headless charmanders

## Web UI

HAROS-FOV web viewer runs on port 4200: `http://localhost:4200`

## Environment

- `HAROS_PORT` — override default port 4200
