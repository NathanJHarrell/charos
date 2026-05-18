# tc-corps

HAROS configuration runner. Reads a HAROS config, populates role prompts with task context, and dispatches agents in the topology the config defines. Agents run in tmux sessions with git worktrees for isolation.

## Usage

```bash
tc-corps launch <config> <brief> [--overlay <overlay>] [--host <host>] [--dry-run]
tc-corps status
tc-corps reap <session>
tc-corps list-configs
tc-corps list-roles
```

## Examples

```bash
tc-corps launch corps grind-phase2-bugs.md --host jarvis-wsl
tc-corps launch scout brief.md --overlay witness
tc-corps status
tc-corps reap corps-20260415
```

## How it relates to `haros`

`haros` is the lower-level battalion CLI (spawn individual agents). `tc-corps` is a higher-level wrapper that reads pre-built configs (defined in `~/haros/configs/`) and orchestrates the whole topology in one command.

Use `tc-corps` when the build shape matches one of the canonical configs. Use `haros` directly for ad-hoc dispatches.

## Related

- `haros` / `haros-dispatch` — the underlying primitives.
- `~/haros/configs/battalion-configs.md` — the canonical list of pre-built configs.
- `~/haros/FRAMEWORK.md` — how HAROS works by role.
