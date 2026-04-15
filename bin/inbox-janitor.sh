#!/run/current-system/sw/bin/bash
# inbox-janitor — autonomous cleanup of ~/Manor/Nathan/inbox
#
# Fires a headless claude instance 3x/day via systemd timer. Reads every
# file in the inbox and moves it to the right Manor room subdir, logs
# every decision to .janitor.log, deletes only empty stubs.
#
# The goal: Dad drops thoughts into note all day long, TC sorts them on
# a schedule without interrupting any in-flight build session.

set -uo pipefail

INBOX="${HOME}/Manor/Nathan/inbox"
MANOR="${HOME}/Manor/Nathan"
LOG="$INBOX/.janitor.log"
RUN_LOG="/var/log/charos/inbox-janitor.log"

mkdir -p "$INBOX" /var/log/charos 2>/dev/null || true

# Skip if nothing to do (ignore dotfiles like .janitor.log)
if ! find "$INBOX" -maxdepth 1 -type f ! -name '.*' | grep -q .; then
  echo "[$(date -Iseconds)] inbox empty — nothing to organize" >> "$RUN_LOG"
  exit 0
fi

read -r -d '' PROMPT <<EOF || true
You are the inbox janitor for Nathan's Manor filesystem. This is an
autonomous run — no human is watching, do not ask questions, just act.

TASK: Clean and organize \`$INBOX\`.

Manor subdir destinations (all under $MANOR/):
  - reference/  → long-term docs, research, how-tos, specs
  - keep/       → things worth archiving but not reference material
  - thinking/   → half-baked ideas, drafts, incomplete thoughts
  - media/      → images, videos, audio, pictures, screenshots
  - personal/   → private/personal notes, journal-like content
  - now/        → active in-progress work for today

RULES:
  1. For each file in the inbox (skip dotfiles), read it and move it to
     the most appropriate Manor subdir via the Bash tool (\`mv\`).
  2. If a file has no meaningful content (just the auto-generated
     "# <title>" header and nothing else), delete it.
  3. If you cannot categorize confidently, LEAVE IT in the inbox.
  4. APPEND (don't overwrite) a line to $LOG for each decision, format:
     YYYY-MM-DDTHH:MM:SS | filename | action | destination_or_reason
  5. NEVER modify files outside \$HOME/Manor/Nathan/. Never modify files
     you move — only move them.
  6. Do not spawn subagents or call any scheduled tasks. Just organize.

When done, print a one-line summary: "organized N | kept N | deleted N".
EOF

echo "[$(date -Iseconds)] inbox-janitor starting" >> "$RUN_LOG"
timeout 300 claude --dangerously-skip-permissions -p "$PROMPT" >> "$RUN_LOG" 2>&1
echo "[$(date -Iseconds)] inbox-janitor exit=$?" >> "$RUN_LOG"
