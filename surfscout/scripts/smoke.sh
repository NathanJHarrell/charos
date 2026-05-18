#!/usr/bin/env bash
# SurfScout end-to-end smoke test — covers Day 1-5 surface.
#
# Prereq: venv bootstrapped + Playwright Chromium installed:
#   cd ~/charos/surfscout
#   python3 -m venv .venv
#   .venv/bin/pip install -e '.[dev]'
#   .venv/bin/playwright install chromium
#
# Replaces the original day1_smoke.sh (kept around for archaeology).

set -euo pipefail

cd "$(dirname "$0")/.."
SURFSCOUT="$(command -v surfscout || echo "$HOME/charos/bin/surfscout")"

echo "═══ SurfScout smoke test ═══════════════════════════════════"
echo "binary: $SURFSCOUT"
echo

echo "[1/9] surfscout --version"
"$SURFSCOUT" --version
echo

echo "[2/9] Tool 1 — read example.com (default Readability path)"
"$SURFSCOUT" read https://example.com --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  title: {d['title']}\")
print(f\"  method: {d['extraction_method']}\")
print(f\"  chars: {d['char_count']}\")
"
echo

echo "[3/9] Tool 1 — read with --no-readability (full body markdownify)"
"$SURFSCOUT" read https://example.com --no-readability --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  method: {d['extraction_method']}\")
print(f\"  chars: {d['char_count']} (should be > the Readability path)\")
"
echo

echo "[4/9] Tool 2 — session start (headless)"
"$SURFSCOUT" session start --headless
echo

echo "[5/9] Tool 2 — ping + navigate + get-url + screenshot"
"$SURFSCOUT" ping
"$SURFSCOUT" navigate https://example.com
"$SURFSCOUT" get-url
"$SURFSCOUT" screenshot
echo

echo "[6/9] Tool 2 — Day 3 action primitives (eval / get-elements / scroll)"
"$SURFSCOUT" eval 'document.title'
"$SURFSCOUT" get-elements 'h1' --limit 3
"$SURFSCOUT" scroll down 300
"$SURFSCOUT" wait 100
echo

echo "[7/9] Tool 2 — Day 4 daemon read (warmed-profile pipeline)"
"$SURFSCOUT" read https://example.com --use-daemon --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d.get('result', d)
print(f\"  method: {r['extraction_method']}\")
print(f\"  chars: {r['char_count']}\")
"
echo

echo "[8/9] Tool 2 — session status + stop"
"$SURFSCOUT" session status
"$SURFSCOUT" session stop
echo

echo "[9/9] Crash recovery — calling daemon after stop should fail loudly"
# `surfscout ping` exits 1 when daemon is dead — that's the expected behavior,
# so we capture both stdout+stderr and grep without pipefail tripping us up.
post_stop_output="$("$SURFSCOUT" ping 2>&1 || true)"
if echo "$post_stop_output" | grep -q "session start"; then
  echo "  ✓ DaemonDeadError surfaced with restart hint"
else
  echo "  ✗ unexpected output from post-stop ping:"
  echo "$post_stop_output"
  exit 1
fi
echo

echo "═══ SurfScout smoke complete ═══════════════════════════════"
