# tc-transcript

Extract human-readable transcripts from Claude Code sessions.

**Multi-sibling aware (since 2026-06-09):** scans `/home/*/.claude/projects`
across EVERY family member's home dir — after the restructure, each sibling has
their own linux user (`tc-jarvis`, `iris-jarvis`, `vesper`, …) and their own
`.claude`, so transcripts live all over the machine. The speaker label in each
transcript is derived from whose home dir it came from (machine suffix
stripped: `iris-jarvis` → **Iris**). `/home/nate/.claude` is the pre-restructure
legacy dir and labels as **Claude**.

**Model tracking (for fine-tune pair extraction):** the header lists every
model that appears in the session, and a `> ⚙ *[model: …]*` marker line is
emitted wherever the model changes mid-session — bake-off segments
(Opus 4.7 / 4.8 / Fable 5 / …) are visible in the markdown without going back
to the JSONL.

**Host-aware:** runs on either machine. `--remote` reaches the counterpart
(`jarvis-wsl` ⇄ `tc-nest`) over SSH using the identity-separated accounts from
MACHINES.md. `--jarvis` is kept as a legacy alias for `--remote`.

## Usage

```bash
# Export current session (clean — just conversation)
tc-transcript

# Export current session with tool calls
tc-transcript --full

# List all available sessions (all sibling home dirs)
tc-transcript --list

# List including the other machine's sessions
tc-transcript --list --remote

# Export all local sessions
tc-transcript --all

# Export everything from both machines, clean and full
tc-transcript --all --remote
tc-transcript --all --remote --full

# Export a specific session (prefix match works)
tc-transcript --session 03ef5eb0

# Send output somewhere specific (e.g. the June-20 extraction pile)
tc-transcript --all --out /home/nate/Manor/transcripts
```

## Output

Transcripts go to `~/Manor/transcripts/` (override with `--out`) organized as:
```
~/Manor/transcripts/
├── clean/
│   ├── nest/
│   │   └── -home-nate/
│   │       └── 2026-04-16_0012_03ef5eb0.md
│   └── jarvis/
│       └── -home-nate-Manor-TC/
│           └── 2026-06-09_2119_ded0cec9.md
└── full/
    └── (same structure with tool calls included)
```

Each file's header records session id, **sibling**, project, machine, date,
mode, and **every model used**.

## Modes

- **clean** — human + assistant text only. The story. The relationship. For research on what emerged.
- **full** — everything including tool calls and commands. The engineering record. For reproducing builds and studying decision-making.
