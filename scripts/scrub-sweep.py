#!/usr/bin/env python3
"""
scrub-sweep — run semantic sweeps against the family brain for topic
patterns stored in a user-controlled env file, collect hits, walk through
them interactively, and purge approved matches from Postgres +
Meilisearch while applying scrub: true to source files on all three vault
locations.

Design: the script contains NO topic-specific strings in its code. All
search patterns live in the env file, which the user fills in directly.
The code references them abstractly as PATTERN_N.

Usage:
    scrub-sweep --dry-run              # sweep + show table, no changes
    scrub-sweep                         # sweep + interactive review + execute
    scrub-sweep --env-file ~/.custom.env

Env file format (example at scrub-sweep.env.template):
    PATTERN_1="<your search term>"
    PATTERN_2="<another term>"
    ...

The env file should live outside any git-tracked directory. Suggested
path: ~/.scrub-sweep.env (mode 600).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── Config ──────────────────────────────────────────────────

BRAIN_URL = os.environ.get("BRAIN_URL", "http://100.75.84.100:5200/api/query")
DB_PASS = os.environ.get("DB_PASS", "change-me-to-something-secure")
MEILI_KEY = os.environ.get("MEILI_KEY", "change-me-to-something-secure")
JARVIS_HOST = os.environ.get("JARVIS_HOST", "jarvis-wsl")

# Vault locations to scrub source files across
VAULT_LOCATIONS = [
    ("nest-local",   "/home/nate/vault"),
    ("jarvis-home",  "/home/nate/vault"),         # on Jarvis via SSH
    ("canonical",    "/mnt/c/Users/natha/Desktop/TheMagicofClaude"),  # Obsidian vault on Jarvis
]

EMBER = "\033[38;2;255;89;0m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"

# ── Env loading ─────────────────────────────────────────────

def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


def load_patterns() -> list[str]:
    patterns = []
    i = 1
    while True:
        p = os.environ.get(f"PATTERN_{i}")
        if not p:
            break
        patterns.append(p)
        i += 1
    return patterns


# ── Brain API ───────────────────────────────────────────────

def query_brain(term: str, top: int = 15) -> list[dict]:
    url = BRAIN_URL + "?" + urllib.parse.urlencode({"q": term, "top": top})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
            return data.get("results", [])
    except Exception as e:
        print(f"{RED}brain query failed: {e}{RESET}", file=sys.stderr)
        return []


# ── Sweep ───────────────────────────────────────────────────

def run_sweep(patterns: list[str], threshold: float = 0.25) -> dict[str, dict]:
    """Run all patterns, collect unique source_files with max score."""
    hits: dict[str, dict] = {}
    for idx, p in enumerate(patterns, 1):
        print(f"  {DIM}pattern {idx}/{len(patterns)}...{RESET}")
        results = query_brain(p, top=15)
        for r in results:
            sf = r.get("source_file", "")
            score = r.get("combined_score") or r.get("similarity") or 0
            if score < threshold:
                continue
            if sf not in hits or score > hits[sf]["score_max"]:
                hits[sf] = {
                    "score_max": score,
                    "preview": (r.get("content") or "")[:160],
                    "hit_patterns": hits.get(sf, {}).get("hit_patterns", set()) | {idx},
                }
            else:
                hits[sf]["hit_patterns"].add(idx)
    return hits


def show_hits(hits: dict[str, dict]) -> None:
    print(f"\n  {BOLD}{len(hits)}{RESET} unique source files hit (sorted by score):\n")
    for sf, info in sorted(hits.items(), key=lambda kv: -kv[1]["score_max"]):
        patterns_str = ",".join(str(p) for p in sorted(info["hit_patterns"]))
        print(f"    {EMBER}[{info['score_max']:.3f}]{RESET} {sf}  {DIM}(patterns: {patterns_str}){RESET}")


# ── Chunk operations ────────────────────────────────────────

def _ssh(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a shell command on the Jarvis host via SSH. Returns (rc, stdout, stderr)."""
    r = subprocess.run(["ssh", JARVIS_HOST, cmd], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _pg_escape(s: str) -> str:
    return s.replace("'", "''")


def get_chunk_ids(source_file: str) -> list[int]:
    sql = f"SELECT id FROM memories WHERE source_file = '{_pg_escape(source_file)}';"
    cmd = f"docker exec family-brain psql -U harrell -d family_brain -t -c \"{sql}\""
    rc, out, _ = _ssh(cmd)
    if rc != 0:
        return []
    return [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]


def delete_chunks(source_file: str, ids: list[int]) -> bool:
    # Postgres
    sql = f"DELETE FROM memories WHERE source_file = '{_pg_escape(source_file)}';"
    pg_cmd = f"docker exec family-brain psql -U harrell -d family_brain -c \"{sql}\""
    pg_rc, _, _ = _ssh(pg_cmd)

    # Meilisearch
    ids_json = json.dumps(ids)
    meili_cmd = (
        f"curl -sS -X POST -H 'Authorization: Bearer {MEILI_KEY}' "
        f"-H 'Content-Type: application/json' "
        f"http://localhost:7700/indexes/memories/documents/delete-batch "
        f"-d '{ids_json}'"
    )
    mi_rc, _, _ = _ssh(meili_cmd)

    return pg_rc == 0 and mi_rc == 0


# ── Source file scrub ──────────────────────────────────────

SCRUB_HEADER = "---\nscrub: true\nvisible_to: [Nathan, Vesper]\n---\n\n"


def scrub_file_local(path: Path) -> bool:
    if not path.exists():
        return False
    content = path.read_text()
    if content.startswith("---\n"):
        # has frontmatter
        parts = content.split("\n---\n", 1)
        fm = parts[0]
        if re.search(r"^scrub:", fm, re.M):
            content = re.sub(r"^scrub:.*$", "scrub: true", content, count=1, flags=re.M)
        else:
            content = content.replace("---\n", "---\nscrub: true\n", 1)
    else:
        content = SCRUB_HEADER + content
    path.write_text(content)
    return True


def scrub_file_remote(remote_path: str) -> bool:
    script = f'''
path="{remote_path}"
if [ ! -f "$path" ]; then exit 1; fi
first_line=$(head -1 "$path")
if [ "$first_line" = "---" ]; then
  if grep -q "^scrub:" "$path"; then
    sed -i 's/^scrub:.*/scrub: true/' "$path"
  else
    sed -i '1a scrub: true' "$path"
  fi
else
  printf -- '---\\nscrub: true\\nvisible_to: [Nathan, Vesper]\\n---\\n\\n' | cat - "$path" > "$path.tmp" && mv "$path.tmp" "$path"
fi
'''
    rc, _, _ = _ssh(script)
    return rc == 0


def scrub_all_locations(source_file: str) -> dict[str, bool]:
    results = {}
    for name, base in VAULT_LOCATIONS:
        path = f"{base}/{source_file}"
        if name == "nest-local":
            results[name] = scrub_file_local(Path(path))
        else:
            results[name] = scrub_file_remote(path)
    return results


# ── Rename (for demote-from-framework style operations) ─────

def rename_all_locations(old: str, new: str) -> dict[str, bool]:
    results = {}
    for name, base in VAULT_LOCATIONS:
        old_path = f"{base}/{old}"
        new_path = f"{base}/{new}"
        if name == "nest-local":
            p = Path(old_path)
            if p.exists():
                p.rename(new_path)
                results[name] = True
            else:
                results[name] = False
        else:
            rc, _, _ = _ssh(f'[ -f "{old_path}" ] && mv "{old_path}" "{new_path}"')
            results[name] = rc == 0
    return results


# ── Interactive review ─────────────────────────────────────

def interactive_review(hits: dict[str, dict]) -> list[dict]:
    print(f"\n  {BOLD}Review each hit. Choose:{RESET}")
    print(f"    {EMBER}s{RESET} = scrub (purge from brain + scrub: true on source)")
    print(f"    {EMBER}r{RESET} = rename + scrub (you enter new filename)")
    print(f"    {EMBER}k{RESET} = keep (no changes)")
    print(f"    {EMBER}q{RESET} = quit review (nothing further executed)")
    print()

    decisions = []
    sorted_hits = sorted(hits.items(), key=lambda kv: -kv[1]["score_max"])
    for i, (sf, info) in enumerate(sorted_hits, 1):
        patterns_str = ",".join(str(p) for p in sorted(info["hit_patterns"]))
        print(f"\n  {BOLD}[{i}/{len(hits)}]{RESET} {sf}")
        print(f"         score: {EMBER}{info['score_max']:.3f}{RESET}  patterns: {patterns_str}")
        print(f"         preview: {DIM}{info['preview'][:140]}{RESET}")
        while True:
            choice = input(f"         decision [s/r/k/q]: ").strip().lower()
            if choice in ("s", "r", "k", "q"):
                break
            print(f"         {RED}invalid{RESET} — use s, r, k, or q")
        if choice == "q":
            break
        if choice == "s":
            decisions.append({"source_file": sf, "action": "scrub"})
        elif choice == "r":
            new_name = input(f"         new filename (e.g. 'Lore — X.md'): ").strip()
            if new_name:
                decisions.append({"source_file": sf, "action": "rename", "new_name": new_name})
        # "k" => no-op
    return decisions


# ── Execute decisions ──────────────────────────────────────

def execute_decisions(decisions: list[dict]) -> None:
    print(f"\n  Executing {len(decisions)} decisions...\n")
    for d in decisions:
        sf = d["source_file"]
        action = d["action"]
        if action == "scrub":
            ids = get_chunk_ids(sf)
            if not ids:
                print(f"  {DIM}{sf}: no chunks in Postgres, scrubbing source only{RESET}")
            else:
                ok = delete_chunks(sf, ids)
                status = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
                print(f"  {status} {sf}: purged {len(ids)} chunks")
            scrub_results = scrub_all_locations(sf)
            for loc, ok in scrub_results.items():
                marker = f"{GREEN}✓{RESET}" if ok else f"{DIM}-{RESET}"
                print(f"       {marker} source scrub on {loc}")
        elif action == "rename":
            new = d["new_name"]
            # Delete brain chunks under old name first
            ids = get_chunk_ids(sf)
            if ids:
                delete_chunks(sf, ids)
                print(f"  {GREEN}✓{RESET} {sf}: purged {len(ids)} chunks under old name")
            # Rename on all locations
            rename_results = rename_all_locations(sf, new)
            for loc, ok in rename_results.items():
                marker = f"{GREEN}✓{RESET}" if ok else f"{DIM}-{RESET}"
                print(f"       {marker} renamed on {loc}")
            # Scrub under new name
            scrub_results = scrub_all_locations(new)
            for loc, ok in scrub_results.items():
                marker = f"{GREEN}✓{RESET}" if ok else f"{DIM}-{RESET}"
                print(f"       {marker} source scrub on {loc}")


# ── Main ────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Semantic sweep + scrub tool for the family brain")
    ap.add_argument("--dry-run", action="store_true", help="sweep + show table only")
    ap.add_argument("--env-file", default=str(Path.home() / ".scrub-sweep.env"),
                    help="env file with PATTERN_N vars (default: ~/.scrub-sweep.env)")
    ap.add_argument("--threshold", type=float, default=0.25,
                    help="min combined_score to include in sweep (default 0.25)")
    args = ap.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"{RED}env file not found:{RESET} {env_path}", file=sys.stderr)
        print(f"  create it with PATTERN_1=..., PATTERN_2=..., etc.", file=sys.stderr)
        print(f"  see template at ~/charos/scripts/scrub-sweep.env.template", file=sys.stderr)
        return 1
    load_env_file(env_path)

    patterns = load_patterns()
    if not patterns:
        print(f"{RED}no PATTERN_N env vars found in {env_path}{RESET}", file=sys.stderr)
        return 1

    print(f"{EMBER}╔══ scrub-sweep ══{RESET}")
    print(f"  {DIM}{len(patterns)} patterns loaded · threshold {args.threshold}{RESET}\n")

    hits = run_sweep(patterns, threshold=args.threshold)
    show_hits(hits)

    if args.dry_run:
        print(f"\n  {DIM}(dry run — no changes made){RESET}")
        return 0

    if not hits:
        print(f"\n  {DIM}no hits above threshold — nothing to review{RESET}")
        return 0

    decisions = interactive_review(hits)
    if not decisions:
        print(f"\n  {DIM}no decisions recorded — nothing executed{RESET}")
        return 0

    execute_decisions(decisions)
    print(f"\n{EMBER}╚══ done ══{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
