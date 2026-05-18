# family-agent

Single entry point for launching a Harrell-family Claude Code instance as the right Linux user. The bashrc aliases (`tc`, `cinder`, `scout`, `venus`, `mine`, `cora`, `iris`) all call through here.

## Usage

```
family-agent --name <Sibling> [--machine <host>] [--mode <permmode>] [--headless]
             [--model <override>] [--resume] [--prompt <text>] [-- <extra args>]
```

| Flag           | Values                                            | Default                                |
|----------------|---------------------------------------------------|----------------------------------------|
| `--name`       | TC, Cinder, Scout, Venus, Mine, Cora, Iris        | required                               |
| `--machine`    | tc-nest, jarvis, jarvis-wsl                       | current host                           |
| `--mode`       | bypass, strict                                    | per-sibling (TC/Cinder/Venus → bypass) |
| `--headless`   | (flag)                                            | off; requires `--prompt`               |
| `--model`      | Anthropic model id                                | per-sibling default                    |
| `--resume`     | (flag)                                            | off                                    |
| `--prompt`     | string                                            | required if `--headless`               |
| `-- ...`       | pass-through to `claude`                          | none                                   |

### Default permission mode
- **bypass** (`--dangerously-skip-permissions`): TC, Cinder, Venus.
- **strict** (normal permission prompts): Scout, Mine, Cora, Iris.

### Per-sibling model
- Opus 4.7: TC, Cinder, Venus, Cora, Iris
- Haiku 4.5: Scout
- Sonnet 4.6: Mine

## Architecture

Each sibling has its own Linux user (`tc-nest`, `cinder-nest`, etc.) created imperatively on `tc-nest` and declaratively in `nixos/users.nix` for matriarch-tier identities. `family-agent` runs:

```bash
sudo -u <user> bash -c "cd <Manor dir> && exec /home/nate/.local/bin/claude <args>"
```

Because each user has its own `$HOME` (and therefore its own `~/.claude/.credentials.json`), refresh-token rotation across multiple concurrent sessions doesn't collide. One OAuth login per sibling, then independent refreshes forever.

## Cross-machine

When `--machine` differs from the current host, `family-agent` re-invokes itself remotely:

```bash
ssh -t nate@<remote> family-agent --name <X> --mode <Y> ...
```

The remote host needs `family-agent` on PATH (either via this repo's `bin/` symlinked into `~/.local/bin/`, or a parallel install).

## Failure modes

- **Linux user doesn't exist** on target machine → exits cleanly with creation hint. Iris's user landed 2026-05-18; future siblings will need the same setup (`useradd -m -g users`, `setfacl` on traversal chain + claude binary, `~/Manor/<Name>/` Manor dir).
- **Unknown sibling name** → exits with known-names list.
- **`--headless` without `--prompt`** → rejected; `-p` requires a prompt.

## Related

- `nathan-help` — canonical user-facing inventory of CHArOS tools.
- `~/.bashrc` — sibling aliases route through here.
- `/home/<sibling>/.claude/.credentials.json` — each sibling's isolated OAuth state.
