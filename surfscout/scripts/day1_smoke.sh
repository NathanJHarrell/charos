#!/usr/bin/env bash
# Day 1 smoke test — verifies the IPC layer round-trips and Tool 1 works.
#
# Prereq: venv bootstrapped + Playwright Chromium installed:
#   cd ~/charos/surfscout
#   python3 -m venv .venv
#   .venv/bin/pip install -e '.[dev]'
#   .venv/bin/playwright install chromium

set -euo pipefail

cd "$(dirname "$0")/.."
SURFSCOUT="$HOME/charos/bin/surfscout"

echo "═══ Day 1 smoke test ═══════════════════════════════════════"

echo "[1/6] surfscout --version"
"$SURFSCOUT" --version
echo

echo "[2/6] Tool 1 — read example.com"
"$SURFSCOUT" read https://example.com --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  url: {d['url']}\")
print(f\"  title: {d['title']}\")
print(f\"  extraction_method: {d['extraction_method']}\")
print(f\"  char_count: {d['char_count']}\")
print(f\"  markdown preview: {d['markdown'][:120]}...\")
"
echo

echo "[3/6] Tool 2 — session start (headless for smoke)"
"$SURFSCOUT" session start --headless
echo

echo "[4/6] Tool 2 — session status"
"$SURFSCOUT" session status
echo

echo "[5/6] Tool 2 — ping + navigate + get-url + screenshot"
"$SURFSCOUT" ping
"$SURFSCOUT" navigate https://example.com
"$SURFSCOUT" get-url
"$SURFSCOUT" screenshot
echo

echo "[6/6] Tool 2 — session stop"
"$SURFSCOUT" session stop
echo

echo "═══ Day 1 smoke complete ═══════════════════════════════════"
