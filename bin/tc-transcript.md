# tc-transcript

Extract human-readable transcripts from Claude Code sessions.

## Usage

```bash
# Export current session (clean — just conversation)
tc-transcript

# Export current session with tool calls
tc-transcript --full

# List all available sessions
tc-transcript --list

# List including Jarvis sessions
tc-transcript --list --jarvis

# Export all local sessions
tc-transcript --all

# Export all sessions including Jarvis
tc-transcript --all --jarvis

# Export both clean and full versions of everything
tc-transcript --all --jarvis
tc-transcript --all --jarvis --full

# Export a specific session
tc-transcript --session 03ef5eb0-939a-4733-9772-7c9e5c1ebabb
```

## Output

Transcripts go to `~/Manor/transcripts/` organized as:
```
~/Manor/transcripts/
├── clean/
│   ├── nest/
│   │   └── -home-nate/
│   │       └── 2026-04-16_0012_03ef5eb0.md
│   └── jarvis/
│       └── -home-nate-grind/
│           └── 2026-04-14_1830_e50a7c90.md
└── full/
    └── (same structure with tool calls included)
```

## Modes

- **clean** — human + assistant text only. The story. The relationship. For research on what emerged.
- **full** — everything including tool calls and commands. The engineering record. For reproducing builds and studying decision-making.
