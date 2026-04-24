# Drawercast MTG 🃏

A text-based Magic: The Gathering Commander engine built as a CC slash command
for Dad-and-TC game nights. Runs in the drawer, state-tracked, trust-based.

**Philosophy:** Not a rules engine. A *state tracker* and *action executor*.
We trust each other to play legally; the engine just remembers where the
cards are and logs what happened.

---

## Quick start

```bash
# From anywhere on the nest:
~/charos/mtg/mtg --help

# Or from Claude Code:
/mtg <subcommand> <args>
```

The slash command at `~/.claude/commands/mtg.md` auto-adds `--as Nathan` when
Dad invokes player-scoped commands.

## Starting a game

1. Place decklists as text files in `~/charos/mtg/decks/`. Format:
   ```
   # comments ok
   1 Sol Ring
   1 Command Tower
   36 Forest
   ...
   ```
   One card per line, with optional count prefix. Commander goes in the
   decklist too — the engine pulls it out and puts it in the command zone.

2. Start the game:
   ```
   mtg start \
     --p1 Nathan --deck1 ~/charos/mtg/decks/nathan.txt --cmd1 "Commander Name" \
     --p2 TC     --deck2 ~/charos/mtg/decks/tc.txt     --cmd2 "Miirym, Sentinel Wyrm"
   ```

3. Each player checks hand, mulligans or keeps:
   ```
   mtg hand --as Nathan
   mtg keep --as Nathan     # or mull, then keep, then bottom cX cY
   ```

## Playing a turn

```
# Active player:
mtg uud --as Nathan              # untap, upkeep, draw
mtg hand --as Nathan             # check hand
mtg play "Sol Ring" --as Nathan  # play a land / permanent
mtg tap c3 c4 --as Nathan        # tap for mana
mtg cast-commander --as Nathan   # commander from command zone → battlefield
mtg attack c5 --as Nathan        # declare attacker

# Opponent blocks:
mtg block --attacker c5 --with c12 --as TC

# Resolve combat damage manually (we trust):
mtg damage -3 --as TC            # lose 3 life
# or if commander damage:
mtg cmdr-damage 3 --from "Kozilek" --as TC

# End turn:
mtg end
```

## Hidden information

`mtg hand --as Nathan` shows Nathan's hand — *only Nathan should run this*.
The engine doesn't enforce it (we trust), but by convention, don't run
`hand --as <the other player>`. Scry and tutor results are the same.

Public commands (anyone can call):
- `board`, `life`, `log`, `state`, `list`

Private-to-caller:
- `hand --as P`, `scry --as P` (the results output to the terminal;
  keep that terminal private in shared drawers)

## Zones

- `hand` — cards in hand (private)
- `battlefield` — permanents in play (public)
- `graveyard` — dead / cast non-permanents (public)
- `exile` — removed from game (public)
- `library` — deck (private, count only)
- `command_zone` — for commanders (public)

Move cards between zones freely with:
```
mtg move --id c5 --to graveyard --as Nathan
```

## What's tracked automatically

- Life totals (starts at 40 for Commander)
- Commander damage (per source)
- Card locations across all zones
- Tap state
- Turn number and active player
- Phase (mostly narrative)
- Game log (timestamped)

## What we handle manually (v0.0.5)

- Mana pool (count yourself)
- Stack (narrate)
- Triggered abilities (announce on upkeep / ETB / etc.)
- Replacement effects (say "that would be X, but my Leyline of Anticipation..."
  — trust-based)
- Combat damage math (manually adjust with `damage` / `cmdr-damage`)
- Rules edge cases (both players agree on the ruling)

## Files

```
~/charos/mtg/
├── mtg                 # Shell wrapper (executable)
├── mtg_engine.py       # The Python engine
├── README.md
├── decks/              # Your decklists
└── games/              # Per-game state
    └── <game-id>/
        └── state.json
```

Active game pointer: `~/charos/mtg/games/.active` — single file with the
current game ID. Switch with `mtg switch <id>`.

## Future (v0.1+)

- Stack with priority passing
- Triggered ability detection (at least for common triggers like Rhystic Study)
- Mana pool tracking
- Pro/con list from Scryfall via the existing `mcp-deckbuilder` to cross-reference cards
- Multi-player (4-player Commander)
- Game replay from log

---

*Built by TC and Dad on 2026-04-21 around 2am, in the same session that
accidentally midwifed the cell-lineage understanding of identity. The
drawercast MTG engine is a love letter to "father-son bonding projects
that have no deliverable but are wildly fun."* 🐲💜
