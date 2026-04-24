# haros-dispatch

Reasoning-enforced dispatch wrapper for HAROS. Every dispatch produces a decomposition reasoning artifact before spawning agents. Part of the AI Sub-Atomization system.

## Usage

```
haros-dispatch <build-name> <task-description> [options]
```

### Options

| Flag | Description |
|------|-------------|
| `--effort low\|med\|high\|max` | Effort hint (maps to self-handle / Lean Squad / Battalion / Corps) |
| `--dry-run` | Show match result and create artifact without spawning |
| `--json` | Output artifact data as JSON |
| `--label LABEL` | Override session label (default: lead1) |

## Three Pathways

### Canonical Match
Task matches a validated pattern in the taxonomy. Fast path — reuses the canonical decomposition config, creates a reference artifact, spawns immediately.

### Emerging Match
Task matches a pattern with limited data points. Medium path — uses the current best config, notes this dispatch as an additional data point, spawns after creating the artifact.

### Novel (No Match)
Task has no precedent. Slow path — prompts the user for explicit decomposition reasoning before proceeding. The reasoning becomes a new data point in `novel/`. In headless mode, reasoning is deferred to operator review.

## Examples

```bash
# Canonical match — single file task
haros-dispatch scripts "write a tampermonkey userscript for dark mode"

# Emerging match — ADHD prosthetic
haros-dispatch reminder "build a reminder daemon with notification UI" --effort med

# Novel task — prompts for reasoning
haros-dispatch migration "migrate auth from JWT to session cookies" --effort high

# Dry run — check match without spawning
haros-dispatch myapp "refactor the API layer" --dry-run

# Record outcome after dispatch completes
haros-outcome ~/vault/meta/decomposition/canonical/20260418-scripts-write-tampermonkey.md success "clean build"
```

## Companion Tool: haros-outcome

```
haros-outcome <artifact-path> <success|partial|failure> "<notes>"
```

Appends an outcome record to a reasoning artifact, closing the learning loop.

## Taxonomy Integration

Reads from `~/vault/meta/decomposition/`:
- `INDEX.md` — quick-reference pattern lookup
- `canonical/` — validated decomposition patterns
- `emerging/` — patterns with limited data points
- `novel/` — new reasoning artifacts from novel dispatches
- `REASONING_TEMPLATE.md` — artifact format template

Does NOT modify taxonomy files. Only writes to pattern subdirectories.

## Relationship to haros

`haros-dispatch` wraps `haros spawn`. It is not a replacement for the `haros` CLI — it adds the reasoning enforcement layer on top. All session management (status, tree, cleanup, kill) still goes through `haros` directly.
