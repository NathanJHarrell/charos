"""
mtg_engine.py — The Drawercast Magic: The Gathering Commander engine.

Philosophy: trust-based. The engine tracks state and executes moves; it does
not enforce all rules. If a player does something illegal, the other player
calls them out. We are not building Arena. We are building the *shape* of
a Commander game we can play together in the drawer.

State is stored in ~/charos/mtg/games/<game-id>/state.json.
The "active" game is tracked in ~/charos/mtg/games/.active.
"""

import json
import random
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from card_cache import fetch_card, bulk_fetch, format_brief, format_full

GAMES_DIR = Path.home() / "charos" / "mtg" / "games"
DECKS_DIR = Path.home() / "charos" / "mtg" / "decks"
ACTIVE = GAMES_DIR / ".active"


# ────────────────────────── state io ──────────────────────────

def load(game_id=None):
    if game_id is None:
        if not ACTIVE.exists():
            die("No active game. Run `mtg start ...` first.")
        game_id = ACTIVE.read_text().strip()
    path = GAMES_DIR / game_id / "state.json"
    if not path.exists():
        die(f"Game '{game_id}' not found at {path}")
    return json.loads(path.read_text())


def save(state):
    path = GAMES_DIR / state["id"] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Snapshot current state into history/ before overwriting (enables undo)
    history_dir = path.parent / "history"
    history_dir.mkdir(exist_ok=True)
    if path.exists():
        existing = path.read_text()
        n = len(list(history_dir.glob("state-*.json")))
        (history_dir / f"state-{n:06d}.json").write_text(existing)

    path.write_text(json.dumps(state, indent=2))
    ACTIVE.write_text(state["id"])


def log(state, msg, visible_to=None):
    """Append an entry to the game log.

    visible_to=None  → public, all players see it
    visible_to=[...] → only listed players + system views see the entry
    """
    ts = datetime.now().strftime("%H:%M:%S")
    if visible_to is None:
        state["log"].append(f"[{ts}] {msg}")
    else:
        state["log"].append({"ts": ts, "msg": msg, "visible_to": list(visible_to)})


def log_visible(entry, viewer=None):
    """Return the formatted string for a log entry if viewer may see it, else None.

    viewer=None means 'full-visibility mode' (game-over reveal, admin, tests).
    """
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        if viewer is None or viewer in entry.get("visible_to", []):
            return f"[{entry['ts']}] {entry['msg']}"
        return None
    return str(entry)


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ────────────────────────── helpers ──────────────────────────

def parse_deck(deck_path):
    """Parse a decklist text file.

    Returns (cards, commander_name_or_None).

    Supported formats for declaring commander (any one works):
      1. `Commander: Atraxa, Praetors' Voice` — explicit marker line
      2. A line `// Commander` (or `# Commander`) followed by the next card line — Moxfield/Archidekt style
      3. No marker at all — caller must pass commander via --cmd1/--cmd2

    Card lines: `1 Card Name`, `1x Card Name`, or `Card Name`.
    Comments: `#` or `//` start a comment line.
    """
    cards = []
    commander = None
    next_card_is_commander = False

    for raw in Path(deck_path).read_text().splitlines():
        line = raw.strip()
        if not line:
            continue

        # "Commander: Foo" explicit marker
        if line.lower().startswith("commander:"):
            commander = line.split(":", 1)[1].strip()
            continue

        # "// Commander" or "# Commander" — next card line is commander
        if line.startswith("#") or line.startswith("//"):
            stripped = line.lstrip("#/").strip()
            if stripped.lower() == "commander" or stripped.lower().startswith("commander "):
                next_card_is_commander = True
            continue  # comment lines never become cards

        # Card line: "1 Card Name" / "1x Card Name" / "Card Name"
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].rstrip("x").isdigit():
            count = int(parts[0].rstrip("x"))
            name = parts[1]
        else:
            count = 1
            name = line

        if next_card_is_commander and commander is None:
            commander = name
            next_card_is_commander = False
            # Don't add to library — commander goes in command zone
            continue

        for _ in range(count):
            cards.append(name)

    return cards, commander


def new_card(name, state):
    cid = f"c{state['next_id']}"
    state["next_id"] += 1
    return {"id": cid, "name": name, "tapped": False, "notes": ""}


def find_player(state, player_name):
    for i, p in enumerate(state["players"]):
        if p["name"].lower() == player_name.lower():
            return i, p
    die(f"Player '{player_name}' not in game. Players: {[p['name'] for p in state['players']]}")


def find_card(state, player, card_id):
    """Find a card by ID anywhere in a player's zones. Returns (zone_name, card, index)."""
    for zone in ("hand", "battlefield", "graveyard", "exile", "library", "command_zone"):
        for i, c in enumerate(player[zone]):
            if c["id"] == card_id:
                return zone, c, i
    return None, None, None


def find_card_by_name(player, name, zone="hand"):
    """Find a card by (case-insensitive, fuzzy-prefix) name in a given zone."""
    name_lower = name.lower().strip().strip('"')
    # Exact first
    for i, c in enumerate(player[zone]):
        if c["name"].lower() == name_lower:
            return c, i
    # Fuzzy startswith
    for i, c in enumerate(player[zone]):
        if c["name"].lower().startswith(name_lower):
            return c, i
    # Fuzzy substring
    for i, c in enumerate(player[zone]):
        if name_lower in c["name"].lower():
            return c, i
    return None, None


def fmt_card(c, verbose=False):
    tap = " ⟲" if c.get("tapped") else ""
    notes = f" ({c['notes']})" if c.get("notes") else ""
    base = f"[{c['id']}] {c['name']}{tap}{notes}"
    if verbose:
        brief = format_brief(c["name"])
        if brief:
            return f"{base}\n         {brief}"
    return base


# ────────────────────────── commands ──────────────────────────

def cmd_start(args):
    """Initialize a new game with two players.

    Usage: mtg start --p1 NAME --deck1 PATH --cmd1 "Commander Name" --p2 NAME --deck2 PATH --cmd2 "Commander Name"
    """
    game_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    state = {
        "id": game_id,
        "created": datetime.now().isoformat(),
        "turn": 0,
        "active_player": 0,
        "phase": "setup",
        "players": [],
        "stack": [],
        "log": [],
        "next_id": 1,
    }

    player_specs = [
        (args.p1, args.deck1, args.cmd1),
        (args.p2, args.deck2, args.cmd2),
    ]
    if getattr(args, "p3", None) and getattr(args, "deck3", None):
        player_specs.append((args.p3, args.deck3, getattr(args, "cmd3", None)))
    if getattr(args, "p4", None) and getattr(args, "deck4", None):
        player_specs.append((args.p4, args.deck4, getattr(args, "cmd4", None)))

    for idx, (name, deck, cmd_arg) in enumerate(player_specs):
        library_cards, deck_commander = parse_deck(deck)
        # Resolve commander: explicit --cmd flag wins, else use deck-declared, else error
        cmd = cmd_arg or deck_commander
        if not cmd:
            die(f"No commander for {name}. Add 'Commander: NAME' to {deck}, or use --cmd{idx+1} flag.")

        # If commander appears in the 99 (e.g. user listed it without using a marker), pull it out
        for n in list(library_cards):
            if n.lower() == cmd.lower():
                library_cards.remove(n)
                break

        # Create card objects
        library = [new_card(n, state) for n in library_cards]
        commander = [new_card(cmd, state)]
        random.shuffle(library)

        state["players"].append({
            "name": name,
            "commander": cmd,
            "life": 40,  # Commander starting life
            "library": library,
            "hand": [],
            "battlefield": [],
            "graveyard": [],
            "exile": [],
            "command_zone": commander,
            "commander_damage": {},
        })

    # Draw 7 for each player
    for p in state["players"]:
        for _ in range(7):
            if p["library"]:
                p["hand"].append(p["library"].pop(0))

    state["active_player"] = random.randint(0, len(state["players"]) - 1)
    state["phase"] = "mulligan"
    log(state, f"Game started. {state['players'][state['active_player']]['name']} goes first (random roll).")
    save(state)

    # Pre-cache all unique card names from both decks from Scryfall
    unique_names = set()
    for p in state["players"]:
        for zone in ("library", "hand", "command_zone"):
            for c in p[zone]:
                unique_names.add(c["name"])
    print(f"📚 Pre-caching {len(unique_names)} unique cards from Scryfall...")
    _, misses = bulk_fetch(sorted(unique_names), quiet=False)
    if misses:
        print(f"  ⚠️  {len(misses)} cards not found on Scryfall (check spelling):")
        for m in misses[:10]:
            print(f"    - {m}")
        if len(misses) > 10:
            print(f"    ... and {len(misses) - 10} more")

    print()
    print(f"🎴 Game {game_id} started.")
    for p in state["players"]:
        print(f"  {p['name']} — commander: {p['commander']} (deck: {len(p['library'])} cards + commander)")
    print(f"  {state['players'][state['active_player']]['name']} goes first.")
    print(f"  All players drew 7. Use `mtg hand --as <name>` to see your hand.")
    print(f"  Mulligan with `mtg mull --as <name>` or keep with `mtg keep --as <name>`.")


def cmd_mull(args):
    """Take a London mulligan — reshuffle, draw 7, put N on bottom where N is mulls taken."""
    state = load()
    _, p = find_player(state, args.player)
    mulls = p.get("mulls_taken", 0) + 1
    p["mulls_taken"] = mulls
    # Reshuffle hand into library
    p["library"].extend(p["hand"])
    p["hand"] = []
    random.shuffle(p["library"])
    # Draw 7
    for _ in range(7):
        if p["library"]:
            p["hand"].append(p["library"].pop(0))
    log(state, f"{p['name']} took mulligan #{mulls}. Now must put {mulls} on bottom after keep.")
    save(state)
    print(f"🔄 {p['name']} mulliganed (#{mulls}). New hand of 7. Use `mtg keep --as {p['name']}` or mull again. After keep, put {mulls} on bottom.")


def cmd_keep(args):
    """Keep the current hand. If mulls > 0, prompt to put N on bottom (handled manually)."""
    state = load()
    _, p = find_player(state, args.player)
    mulls = p.get("mulls_taken", 0)
    log(state, f"{p['name']} kept (after {mulls} mulligan(s)).")
    # Check if both players have kept
    both_kept = all("kept" in pl or pl.get("mulls_taken", 0) == 0 or "kept" in pl for pl in state["players"])
    p["kept"] = True
    if all(pl.get("kept") for pl in state["players"]):
        state["phase"] = "main1"
        state["turn"] = 1
        log(state, f"All players kept. Turn 1, active: {state['players'][state['active_player']]['name']}.")
    save(state)
    if mulls > 0:
        print(f"✋ {p['name']} kept. Put {mulls} card(s) on bottom of library. Use `mtg bottom --as {p['name']} <id1> <id2> ...`")
    else:
        print(f"✋ {p['name']} kept on 7.")
    if state["phase"] == "main1":
        print(f"🎬 Turn 1 begins. Active player: {state['players'][state['active_player']]['name']}")


def cmd_bottom(args):
    """Put specified card IDs from hand onto bottom of library (post-mulligan)."""
    state = load()
    _, p = find_player(state, args.player)
    for cid in args.ids:
        for i, c in enumerate(p["hand"]):
            if c["id"] == cid:
                p["library"].append(p["hand"].pop(i))
                break
        else:
            print(f"  (warning: {cid} not in hand)")
    log(state, f"{p['name']} put {len(args.ids)} cards on bottom.")
    save(state)
    print(f"⬇️  {p['name']} bottomed {len(args.ids)} cards. Hand: {len(p['hand'])}")


def cmd_hand(args):
    state = load()
    _, p = find_player(state, args.player)
    print(f"✋ {p['name']}'s hand ({len(p['hand'])} cards):")
    for c in p["hand"]:
        print(f"  {fmt_card(c, verbose=True)}")


def cmd_board(args):
    state = load()
    print(f"🎴 Turn {state['turn']}, phase: {state['phase']}, active: {state['players'][state['active_player']]['name']}")
    for p in state["players"]:
        print(f"\n━━ {p['name']} (life {p['life']}) ━━")
        print(f"  Commander zone: {', '.join(fmt_card(c) for c in p['command_zone']) or '(empty)'}")
        print(f"  Battlefield ({len(p['battlefield'])}):")
        for c in p["battlefield"]:
            print(f"    {fmt_card(c)}")
        print(f"  Hand: {len(p['hand'])} | Library: {len(p['library'])} | Graveyard: {len(p['graveyard'])} | Exile: {len(p['exile'])}")


def cmd_life(args):
    state = load()
    print("💚 Life totals:")
    for p in state["players"]:
        cd = ", ".join(f"{src}: {n}" for src, n in p["commander_damage"].items()) or "none"
        print(f"  {p['name']}: {p['life']}  (cmdr dmg from: {cd})")


def cmd_play(args):
    """Move a card from hand to battlefield."""
    state = load()
    _, p = find_player(state, args.player)
    c, i = find_card_by_name(p, args.name, "hand")
    if not c:
        die(f"'{args.name}' not in {p['name']}'s hand.")
    p["hand"].pop(i)
    p["battlefield"].append(c)
    log(state, f"{p['name']} played {c['name']} ({c['id']}).")
    save(state)
    print(f"🎴 {p['name']} played {fmt_card(c)} onto battlefield.")


def cmd_cast_commander(args):
    """Move commander from command zone to battlefield."""
    state = load()
    _, p = find_player(state, args.player)
    if not p["command_zone"]:
        die(f"{p['name']} has no commander in command zone.")
    c = p["command_zone"].pop(0)
    # Track cast count for tax
    c["notes"] = c.get("notes", "")
    cast_count = c.get("cast_count", 0) + 1
    c["cast_count"] = cast_count
    p["battlefield"].append(c)
    tax = (cast_count - 1) * 2
    log(state, f"{p['name']} cast commander {c['name']} (cast #{cast_count}, tax +{tax}).")
    save(state)
    print(f"👑 {p['name']} cast {fmt_card(c)} from command zone. Cast #{cast_count}, commander tax +{tax} generic mana.")


def cmd_tap(args):
    state = load()
    _, p = find_player(state, args.player)
    for cid in args.ids:
        zone, c, i = find_card(state, p, cid)
        if c is None:
            print(f"  (warning: {cid} not found for {p['name']})")
            continue
        c["tapped"] = True
    log(state, f"{p['name']} tapped {', '.join(args.ids)}.")
    save(state)
    print(f"⟲ Tapped: {', '.join(args.ids)}")


def cmd_untap(args):
    state = load()
    _, p = find_player(state, args.player)
    if args.ids:
        for cid in args.ids:
            _, c, _ = find_card(state, p, cid)
            if c:
                c["tapped"] = False
    else:
        # Untap all
        for c in p["battlefield"]:
            c["tapped"] = False
    log(state, f"{p['name']} untapped {args.ids or 'all'}.")
    save(state)
    print(f"⟳ Untapped: {args.ids or 'all'}")


def cmd_move(args):
    """Move a card between zones. mtg move --as P --id cX --to graveyard"""
    state = load()
    _, p = find_player(state, args.player)
    zone, c, i = find_card(state, p, args.id)
    if c is None:
        die(f"Card {args.id} not found for {p['name']}.")
    p[zone].pop(i)
    p[args.to].append(c)
    log(state, f"{p['name']} moved {c['name']} ({c['id']}) from {zone} → {args.to}.")
    save(state)
    print(f"📦 Moved {fmt_card(c)}: {zone} → {args.to}")


def cmd_draw(args):
    state = load()
    _, p = find_player(state, args.player)
    drawn = []
    for _ in range(args.n):
        if p["library"]:
            drawn.append(p["library"].pop(0))
            p["hand"].append(drawn[-1])
    log(state, f"{p['name']} drew {len(drawn)} cards.")
    save(state)
    print(f"🎴 {p['name']} drew {len(drawn)} card(s): {', '.join(c['name'] for c in drawn)}")


def cmd_mill(args):
    state = load()
    _, p = find_player(state, args.player)
    milled = []
    for _ in range(args.n):
        if p["library"]:
            milled.append(p["library"].pop(0))
            p["graveyard"].append(milled[-1])
    log(state, f"{p['name']} milled {len(milled)}: {', '.join(c['name'] for c in milled)}")
    save(state)
    print(f"🪦 {p['name']} milled: {', '.join(c['name'] for c in milled)}")


def cmd_search(args):
    """Tutor: find a card in library, shuffle, then place it in chosen zone."""
    state = load()
    _, p = find_player(state, args.player)
    target = args.name.lower().strip().strip('"')
    for i, c in enumerate(p["library"]):
        if target in c["name"].lower():
            found = p["library"].pop(i)
            random.shuffle(p["library"])
            if args.to == "top":
                p["library"].insert(0, found)
                dest_label = "top of library"
            elif args.to == "bottom":
                p["library"].append(found)
                dest_label = "bottom of library"
            else:  # hand
                p["hand"].append(found)
                dest_label = "hand"
            # Public: someone tutored (and where to, for top/bottom/hand). Private: the card name.
            log(state, f"{p['name']} tutored a card to {dest_label} (library shuffled).")
            log(state, f"{p['name']} tutored {found['name']} ({found['id']}) to {dest_label}.", visible_to=[p['name']])
            save(state)
            print(f"🔍 {p['name']} tutored {fmt_card(found)} → {dest_label}. Library shuffled.")
            return
    die(f"'{args.name}' not found in {p['name']}'s library.")


def cmd_scry(args):
    """Look at top N of library. Prints privately; rearrangement is manual via `bottom` or keep."""
    state = load()
    _, p = find_player(state, args.player)
    n = args.n
    top = p["library"][:n]
    print(f"🔮 {p['name']} scries {n}. Top of library (in order):")
    for c in top:
        print(f"  {fmt_card(c)}")
    print(f"  Use `mtg move --as {p['name']} --id <cid> --to library` (to bottom) or leave on top.")
    log(state, f"{p['name']} scried {n}.")
    log(state, f"{p['name']} scry top: {[c['name'] for c in top]}", visible_to=[p['name']])


def cmd_shuffle(args):
    state = load()
    _, p = find_player(state, args.player)
    random.shuffle(p["library"])
    log(state, f"{p['name']} shuffled library.")
    save(state)
    print(f"🌀 {p['name']} shuffled library ({len(p['library'])} cards).")


def cmd_damage(args):
    """Adjust a player's life total. Positive = gain, negative = lose."""
    state = load()
    _, p = find_player(state, args.player)
    before = p["life"]
    p["life"] += args.amount
    log(state, f"{p['name']} {'gained' if args.amount > 0 else 'lost'} {abs(args.amount)} life ({before} → {p['life']}).")
    save(state)
    arrow = "💚" if args.amount > 0 else "🩸"
    print(f"{arrow} {p['name']}: {before} → {p['life']}")


def cmd_cmdr_damage(args):
    """Apply commander damage. --to P --from "Commander Name" --n N"""
    state = load()
    _, p = find_player(state, args.player)
    p["commander_damage"][args.from_name] = p["commander_damage"].get(args.from_name, 0) + args.n
    p["life"] -= args.n
    log(state, f"{p['name']} took {args.n} commander damage from {args.from_name}. Total: {p['commander_damage'][args.from_name]}.")
    save(state)
    print(f"👑🩸 {p['name']} took {args.n} commander damage from {args.from_name}. Total from them: {p['commander_damage'][args.from_name]}/21. Life: {p['life']}")
    if p["commander_damage"][args.from_name] >= 21:
        print(f"  💀 {p['name']} has lost to commander damage!")


def cmd_attack(args):
    """Declare attackers. Just taps them and logs; damage is resolved separately."""
    state = load()
    _, p = find_player(state, args.player)
    attackers = []
    for cid in args.ids:
        _, c, _ = find_card(state, p, cid)
        if c:
            c["tapped"] = True
            attackers.append(c)
    log(state, f"{p['name']} attacks with {', '.join(a['name'] for a in attackers)}.")
    save(state)
    print(f"⚔️  {p['name']} attacks with: {', '.join(fmt_card(a) for a in attackers)}")
    print(f"   (opponent: declare blockers with `mtg block --as YOU --attacker cX --with cY`)")


def cmd_block(args):
    """Declare a blocker. --attacker cX --with cY[,cZ...]"""
    state = load()
    _, p = find_player(state, args.player)
    blockers = []
    for cid in args.blockers:
        _, c, _ = find_card(state, p, cid)
        if c:
            blockers.append(c)
    log(state, f"{p['name']} blocks {args.attacker} with {', '.join(b['name'] for b in blockers)}.")
    save(state)
    print(f"🛡️  {p['name']} blocks {args.attacker} with: {', '.join(fmt_card(b) for b in blockers)}")


def cmd_uud(args):
    """Untap, upkeep, draw for the active player."""
    state = load()
    idx, p = find_player(state, args.player)
    if idx != state["active_player"]:
        print(f"⚠️  Warning: {p['name']} is not the active player (active is {state['players'][state['active_player']]['name']}).")
    # Untap
    for c in p["battlefield"]:
        c["tapped"] = False
    # Draw (skip if turn 1 active player, but we'll leave that to the players to enforce)
    drawn = None
    if p["library"]:
        drawn = p["library"].pop(0)
        p["hand"].append(drawn)
    state["phase"] = "main1"
    # Public: UUD happened. Private: the card drawn.
    log(state, f"{p['name']} UUD: untapped all, drew 1 card.")
    if drawn:
        log(state, f"{p['name']} drew {drawn['name']} ({drawn['id']}).", visible_to=[p['name']])
    else:
        log(state, f"{p['name']} tried to draw from empty library.")
    save(state)
    print(f"☀️  {p['name']} untap. Upkeep (declare any triggers). Draw: {drawn['name'] if drawn else 'nothing — library empty, take a loss trigger'}.")


def cmd_end(args):
    """End current turn, pass to next player (skipping eliminated)."""
    state = load()
    if state.get("game_over"):
        die("Game is over. Start a new game with `mtg start`.")
    n = len(state["players"])
    nxt = (state["active_player"] + 1) % n
    # Skip eliminated players
    guard = 0
    while state["players"][nxt].get("eliminated") and guard < n:
        nxt = (nxt + 1) % n
        guard += 1
    if guard >= n:
        die("No live players remain.")
    state["active_player"] = nxt
    state["turn"] += 1
    state["phase"] = "untap"
    active = state["players"][state["active_player"]]["name"]
    log(state, f"Turn {state['turn']} begins. Active: {active}.")
    save(state)
    print(f"🔄 Turn {state['turn']}. Active player: {active}. Run `mtg uud --as {active}` to untap/upkeep/draw.")


def _check_winner(state):
    """If exactly one non-eliminated player remains, mark them winner and end the game."""
    alive = [p for p in state["players"] if not p.get("eliminated")]
    if len(alive) == 1 and not state.get("game_over"):
        winner = alive[0]
        state["winner"] = winner["name"]
        state["game_over"] = True
        log(state, f"🏆 {winner['name']} wins the game!")
        return winner["name"]
    if len(alive) == 0 and not state.get("game_over"):
        state["game_over"] = True
        log(state, "Game ended — no players remaining (draw).")
    return None


def cmd_concede(args):
    """Player concedes — marks them eliminated. Triggers winner check."""
    state = load()
    if state.get("game_over"):
        die("Game is already over.")
    _, p = find_player(state, args.player)
    if p.get("eliminated"):
        die(f"{p['name']} already conceded / was eliminated.")
    p["eliminated"] = True
    p["concede_reason"] = args.reason or "conceded"
    msg = f"{p['name']} conceded"
    if args.reason:
        msg += f": {args.reason}"
    msg += "."
    log(state, msg)
    winner = _check_winner(state)
    save(state)
    print(f"🏳️  {p['name']} conceded.")
    if winner:
        print(f"🏆 {winner} wins!")


def cmd_eliminate(args):
    """Mark a player as eliminated via life loss, commander damage, mill, or effect."""
    state = load()
    if state.get("game_over"):
        die("Game is already over.")
    _, p = find_player(state, args.target)
    if p.get("eliminated"):
        die(f"{p['name']} already eliminated.")
    p["eliminated"] = True
    reason_by = args.by
    attr = f" (from {args.from_player})" if args.from_player else ""
    p["elim_reason"] = f"{reason_by}{attr}"
    log(state, f"{p['name']} eliminated by {reason_by}{attr}.")
    winner = _check_winner(state)
    save(state)
    print(f"💀 {p['name']} eliminated ({reason_by}{attr}).")
    if winner:
        print(f"🏆 {winner} wins!")


def cmd_discard(args):
    """Discard specific cards from hand to graveyard (end-step hand-size or effect-based)."""
    state = load()
    _, p = find_player(state, args.player)
    discarded = []
    for cid in args.ids:
        for i, c in enumerate(p["hand"]):
            if c["id"] == cid:
                p["hand"].pop(i)
                p["graveyard"].append(c)
                discarded.append(c["name"])
                break
        else:
            print(f"  (warning: {cid} not in {p['name']}'s hand)")
    log(state, f"{p['name']} discarded: {', '.join(discarded) if discarded else '(nothing)'}.")
    save(state)
    print(f"🗑️  {p['name']} discarded {len(discarded)} card(s): {', '.join(discarded)}")


def cmd_undo(args):
    """Roll back the last N state changes. Defaults to 1."""
    if not ACTIVE.exists():
        die("No active game.")
    game_id = ACTIVE.read_text().strip()
    history_dir = GAMES_DIR / game_id / "history"
    if not history_dir.exists():
        die("No history for this game.")
    snapshots = sorted(history_dir.glob("state-*.json"))
    if not snapshots:
        die("Nothing to undo.")
    n = args.n
    if n > len(snapshots):
        print(f"⚠️  Only {len(snapshots)} snapshots available; undoing all of them.")
        n = len(snapshots)
    # Keep the (N-th from end) snapshot as the new current state; discard anything after it
    target = snapshots[-n]
    current_path = GAMES_DIR / game_id / "state.json"
    current_path.write_text(target.read_text())
    # Delete the snapshots we rolled past (including the one we restored, since it's now state.json)
    for s in snapshots[-n:]:
        s.unlink()
    state = load()
    print(f"↩️  Undid {n} step(s). Current log tail:")
    for line in state["log"][-5:]:
        print(f"  {line}")


def cmd_turn(args):
    """Start-of-turn convenience: log tail + UUD + board + hand, in one command."""
    state = load()
    # Log tail
    print("📜 Recent log:")
    for line in state["log"][-8:]:
        print(f"  {line}")
    print()
    # UUD
    print("────────────────────────────────")
    cmd_uud(args)
    print()
    # Board
    print("────────────────────────────────")
    cmd_board(args)
    print()
    # Hand
    print("────────────────────────────────")
    cmd_hand(args)


def cmd_card(args):
    """Show full oracle text for a card by ID (anywhere) or name (Scryfall lookup)."""
    query = args.query.strip().strip('"')
    # If it looks like a card ID (cN), find it in current game
    if query.startswith("c") and query[1:].isdigit():
        state = load()
        for p in state["players"]:
            for zone in ("hand", "battlefield", "graveyard", "exile", "library", "command_zone"):
                for c in p[zone]:
                    if c["id"] == query:
                        print(format_full(c["name"]))
                        return
        die(f"Card ID {query} not found in current game.")
    else:
        print(format_full(query))


def cmd_note(args):
    state = load()
    log(state, f"NOTE: {args.text}")
    save(state)
    print(f"📝 Noted: {args.text}")


def cmd_log(args):
    state = load()
    n = args.n or 20
    viewer = getattr(args, "player", None)
    header = f"📜 Last {n} log entries"
    if viewer:
        header += f" (visible to {viewer})"
    if state.get("game_over"):
        header += " — FULL REVEAL (game over)"
        viewer = None
    print(f"{header}:")
    visible = [log_visible(e, viewer) for e in state["log"]]
    visible = [v for v in visible if v is not None]
    for line in visible[-n:]:
        print(f"  {line}")

    if args.follow:
        import time as _time
        last_len = len(state["log"])
        print("\n📡 Following log (Ctrl+C to stop)...")
        try:
            while True:
                _time.sleep(0.5)
                state = load()
                new_entries = state["log"][last_len:]
                for e in new_entries:
                    v = log_visible(e, None if state.get("game_over") else viewer)
                    if v is not None:
                        print(f"  {v}")
                last_len = len(state["log"])
        except KeyboardInterrupt:
            print("\n📡 Stopped following.")


def cmd_state(args):
    state = load()
    print(json.dumps(state, indent=2))


def cmd_list(args):
    """List all games."""
    if not GAMES_DIR.exists():
        print("(no games)")
        return
    games = sorted([d.name for d in GAMES_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")])
    active = ACTIVE.read_text().strip() if ACTIVE.exists() else None
    for g in games:
        marker = " ← active" if g == active else ""
        print(f"  {g}{marker}")


def cmd_switch(args):
    """Switch to a different game."""
    state = load(args.game_id)
    save(state)
    print(f"✅ Active game: {args.game_id}")


# ────────────────────────── cli ──────────────────────────

def main():
    p = argparse.ArgumentParser(prog="mtg", description="Drawercast MTG Commander engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    # start
    s = sub.add_parser("start", help="Start a new game")
    s.add_argument("--p1", required=True, help="Player 1 name")
    s.add_argument("--deck1", required=True, help="Path to player 1 decklist")
    s.add_argument("--cmd1", help="Player 1 commander name (optional if deck file has 'Commander: NAME')")
    s.add_argument("--p2", required=True, help="Player 2 name")
    s.add_argument("--deck2", required=True, help="Path to player 2 decklist")
    s.add_argument("--cmd2", help="Player 2 commander name (optional if deck file has 'Commander: NAME')")
    s.add_argument("--p3", help="Player 3 name (optional, for 3-player pods)")
    s.add_argument("--deck3", help="Path to player 3 decklist")
    s.add_argument("--cmd3", help="Player 3 commander name")
    s.add_argument("--p4", help="Player 4 name (optional, for 4-player pods)")
    s.add_argument("--deck4", help="Path to player 4 decklist")
    s.add_argument("--cmd4", help="Player 4 commander name")
    s.set_defaults(func=cmd_start)

    # mulligan flow
    s = sub.add_parser("mull", help="Take a mulligan (London)")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_mull)

    s = sub.add_parser("keep", help="Keep your opening hand")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_keep)

    s = sub.add_parser("bottom", help="Put cards from hand on bottom after mulligan")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("ids", nargs="+", help="Card IDs to bottom")
    s.set_defaults(func=cmd_bottom)

    # views
    s = sub.add_parser("hand", help="Show a player's hand (private to them)")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_hand)

    s = sub.add_parser("board", help="Show full battlefield state")
    s.set_defaults(func=cmd_board)

    s = sub.add_parser("life", help="Show life totals + commander damage")
    s.set_defaults(func=cmd_life)

    # actions
    s = sub.add_parser("play", help="Play a card from hand to battlefield")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("name", help="Card name (fuzzy match)")
    s.set_defaults(func=cmd_play)

    s = sub.add_parser("cast-commander", help="Cast commander from command zone")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_cast_commander)

    s = sub.add_parser("tap", help="Tap cards")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("ids", nargs="+")
    s.set_defaults(func=cmd_tap)

    s = sub.add_parser("untap", help="Untap cards (or all if no ids)")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("ids", nargs="*")
    s.set_defaults(func=cmd_untap)

    s = sub.add_parser("move", help="Move a card between zones")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("--id", dest="id", required=True)
    s.add_argument("--to", required=True, choices=["hand", "battlefield", "graveyard", "exile", "library", "command_zone"])
    s.set_defaults(func=cmd_move)

    s = sub.add_parser("draw", help="Draw N cards")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("n", type=int)
    s.set_defaults(func=cmd_draw)

    s = sub.add_parser("mill", help="Mill N cards")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("n", type=int)
    s.set_defaults(func=cmd_mill)

    s = sub.add_parser("search", help="Tutor a card from library to hand/top/bottom (shuffles after)")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("name")
    s.add_argument("--to", choices=["hand", "top", "bottom"], default="hand", help="Destination (default: hand)")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("scry", help="Look at top N of library")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("n", type=int)
    s.set_defaults(func=cmd_scry)

    s = sub.add_parser("shuffle", help="Shuffle your library")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_shuffle)

    # life changes
    s = sub.add_parser("damage", help="Gain or lose life (use negative for loss)")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("amount", type=int)
    s.set_defaults(func=cmd_damage)

    s = sub.add_parser("cmdr-damage", help="Take commander damage")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("--from", dest="from_name", required=True, help="Commander name dealing damage")
    s.add_argument("n", type=int)
    s.set_defaults(func=cmd_cmdr_damage)

    # combat
    s = sub.add_parser("attack", help="Declare attackers")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("ids", nargs="+")
    s.set_defaults(func=cmd_attack)

    s = sub.add_parser("block", help="Declare a blocker")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("--attacker", required=True)
    s.add_argument("--with", dest="blockers", nargs="+", required=True)
    s.set_defaults(func=cmd_block)

    # turn flow
    s = sub.add_parser("uud", help="Untap, Upkeep, Draw (active player only)")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_uud)

    s = sub.add_parser("end", help="End turn, pass to next player")
    s.set_defaults(func=cmd_end)

    # log / state
    s = sub.add_parser("discard", help="Discard card(s) from hand to graveyard")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("ids", nargs="+", help="Card IDs from hand to discard")
    s.set_defaults(func=cmd_discard)

    s = sub.add_parser("undo", help="Roll back the last N state changes (default 1)")
    s.add_argument("-n", type=int, default=1, help="Number of steps to undo")
    s.set_defaults(func=cmd_undo)

    s = sub.add_parser("turn", help="Start-of-turn combo: log + UUD + board + hand")
    s.add_argument("--as", dest="player", required=True)
    s.set_defaults(func=cmd_turn)

    s = sub.add_parser("card", help="Show full oracle text for a card by ID (cN) or name")
    s.add_argument("query", help="Card ID (cN) or card name")
    s.set_defaults(func=cmd_card)

    s = sub.add_parser("note", help="Log a free-text note in the game log")
    s.add_argument("text")
    s.set_defaults(func=cmd_note)

    s = sub.add_parser("log", help="Show the game log (or follow with -f)")
    s.add_argument("-n", type=int, default=20)
    s.add_argument("-f", "--follow", action="store_true", help="Stream new log entries as they arrive")
    s.add_argument("--as", dest="player", help="View log as a specific player (hides private entries not visible to them)")
    s.set_defaults(func=cmd_log)

    # concede / eliminate
    s = sub.add_parser("concede", help="Player concedes the game")
    s.add_argument("--as", dest="player", required=True)
    s.add_argument("--reason", default="", help="Optional concede message")
    s.set_defaults(func=cmd_concede)

    s = sub.add_parser("eliminate", help="Mark a player as eliminated (life=0, cmdr-dmg 21, etc.)")
    s.add_argument("--target", required=True, help="Player to eliminate")
    s.add_argument("--by", default="damage", help="Cause: life, cmdr, mill, effect")
    s.add_argument("--from-player", help="Attributed cause (for cmdr damage etc)")
    s.set_defaults(func=cmd_eliminate)

    s = sub.add_parser("state", help="Dump full game state (debug)")
    s.set_defaults(func=cmd_state)

    s = sub.add_parser("list", help="List all games")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("switch", help="Switch active game")
    s.add_argument("game_id")
    s.set_defaults(func=cmd_switch)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
