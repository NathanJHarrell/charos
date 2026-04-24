"""
card_cache.py — Scryfall-backed card lookup with local JSON cache.

Usage:
    data = fetch_card("Lightning Bolt")
    # returns dict with name, mana_cost, type_line, oracle_text, power, toughness, ...

Cache lives in ~/charos/mtg/card_cache/<slug>.json.
Respects Scryfall's 100ms rate-limit courtesy.
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

CACHE_DIR = Path.home() / "charos" / "mtg" / "card_cache"
SCRYFALL_NAMED = "https://api.scryfall.com/cards/named"
REQUEST_INTERVAL_S = 0.11  # Scryfall asks for >= 100ms between requests
_last_request_time = 0.0

# Scryfall asks clients to identify themselves via User-Agent + Accept headers
HEADERS = {
    "User-Agent": "drawercast-mtg/0.0.5 (https://github.com/charos family build)",
    "Accept": "application/json",
}


def _get(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _slug(name: str) -> str:
    """Slugify card name for filesystem-safe cache key."""
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def _rate_limit():
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL_S:
        time.sleep(REQUEST_INTERVAL_S - elapsed)
    _last_request_time = time.monotonic()


def _slim(data: dict) -> dict:
    """Extract the fields we actually display, discard the rest."""
    # Handle double-faced cards (take front face) if applicable
    if "card_faces" in data and not data.get("oracle_text") and data["card_faces"]:
        front = data["card_faces"][0]
        oracle = front.get("oracle_text", "")
        mana_cost = front.get("mana_cost", "")
        type_line = front.get("type_line", data.get("type_line", ""))
        power = front.get("power", data.get("power", ""))
        toughness = front.get("toughness", data.get("toughness", ""))
    else:
        oracle = data.get("oracle_text", "")
        mana_cost = data.get("mana_cost", "")
        type_line = data.get("type_line", "")
        power = data.get("power", "")
        toughness = data.get("toughness", "")

    return {
        "name": data.get("name", ""),
        "mana_cost": mana_cost,
        "cmc": data.get("cmc", 0),
        "type_line": type_line,
        "oracle_text": oracle,
        "power": power,
        "toughness": toughness,
        "colors": data.get("colors", []),
        "color_identity": data.get("color_identity", []),
    }


def fetch_card(name: str, use_cache: bool = True) -> dict | None:
    """Look up a card by exact name, with disk caching. Returns None on miss."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{_slug(name)}.json"

    if use_cache and cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            pass  # fall through to refresh

    _rate_limit()
    url = f"{SCRYFALL_NAMED}?exact={urllib.parse.quote(name)}"
    try:
        raw = _get(url)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            # Try fuzzy as fallback for typos / ambiguous names
            _rate_limit()
            url = f"{SCRYFALL_NAMED}?fuzzy={urllib.parse.quote(name)}"
            try:
                raw = _get(url)
            except Exception:
                return None
        else:
            return None
    except Exception:
        return None

    slim = _slim(raw)
    cache_path.write_text(json.dumps(slim, indent=2))
    return slim


def bulk_fetch(names: list[str], quiet: bool = False) -> dict:
    """Prime the cache with a list of card names. Returns {name: data_or_None}."""
    results = {}
    misses = []
    for i, name in enumerate(names):
        data = fetch_card(name)
        results[name] = data
        if data is None:
            misses.append(name)
        if not quiet and (i + 1) % 20 == 0:
            print(f"  Pre-cached {i+1}/{len(names)}...")
    return results, misses


def format_brief(name: str) -> str:
    """Return `{mana} Type Line (P/T)` for a card, or just the name if unknown."""
    data = fetch_card(name)
    if not data:
        return ""
    bits = []
    if data["mana_cost"]:
        bits.append(data["mana_cost"])
    if data["type_line"]:
        bits.append(data["type_line"])
    if data["power"] and data["toughness"]:
        bits.append(f"({data['power']}/{data['toughness']})")
    return "  ".join(bits)


def format_full(name: str) -> str:
    """Return a multi-line card description with oracle text."""
    data = fetch_card(name)
    if not data:
        return f"{name}\n  (card data not found in Scryfall)"
    lines = [data["name"]]
    header_bits = []
    if data["mana_cost"]:
        header_bits.append(data["mana_cost"])
    if data["type_line"]:
        header_bits.append(data["type_line"])
    if data["power"] and data["toughness"]:
        header_bits.append(f"({data['power']}/{data['toughness']})")
    if header_bits:
        lines.append("  " + "  ·  ".join(header_bits))
    if data["oracle_text"]:
        for ol in data["oracle_text"].splitlines():
            lines.append(f"  {ol}")
    return "\n".join(lines)
