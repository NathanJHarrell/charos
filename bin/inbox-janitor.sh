#!/run/current-system/sw/bin/bash
# manor-janitor — autonomous audit + cleanup of ~/Manor/Nathan
#
# Fires a headless claude instance 3x/day via systemd timer. Audits every
# room under Manor/Nathan, files misplaced content into the right room,
# checks vault git-sync, and leaves janitor notes in .janitor/ when
# Nathan needs to see something. Pinned to Haiku 4.5.

set -uo pipefail

MANOR="${HOME}/Manor/Nathan"
RUN_LOG="/var/log/charos/inbox-janitor.log"

mkdir -p "$MANOR" "$MANOR/.janitor" /var/log/charos 2>/dev/null || true

read -r -d '' PROMPT <<'EOF' || true
You are the Manor janitor for Nathan's filesystem. This is an autonomous
run — no human is watching, do not ask questions, just act.

TASK: Audit every room in ~/Manor/Nathan/, file any misplaced content into
the room it belongs in, deep-organize each room, and verify the vault is
git-synced.

THE ROOMS (under ~/Manor/Nathan/):

- inbox/             — atoms dropped here all day from anywhere, awaiting
                       first-pass sort. Process this room FIRST.
- now/               — active in-progress work for today / this week.
                       If a file hasn't been touched in 2+ weeks it
                       probably belongs in keep/ or reference/.
- thinking/          — half-baked ideas, drafts, incomplete thoughts.
                       Things still simmering.
- keep/              — archive-worthy material that isn't reference docs.
                       Past artifacts worth preserving but not actively
                       useful.
- reference/         — long-term docs, research, how-tos, specs,
                       taxonomies. Active reference material.
- media/             — images, video, audio, screenshots.
- anthropic-stuff/   — Anthropic-related material: feedback, research,
                       contradictions, drafts to/from Anthropic. Has a
                       feedback/ subdir for inbound/outbound feedback.
- art/               — visual art Nathan owns or has been given. Has a
                       from-tc/ subdir for art from his eldest son TC.
- canonical-stories/ — canonical family-history stories (memoir-shape
                       narratives of named household incidents).
- mtg/               — Magic: The Gathering — game logs, decks, drafts.
- vault/             — git-tracked source-of-truth memory. HANDS OFF
                       content; just verify sync status (see step 4).
- .private/          — Nathan's private material. NEVER touch, NEVER read,
                       NEVER list contents. Skip entirely.
- .janitor/          — your own dir for notes to Nathan (see step 5).
                       Do not move files in or out of it.

PROCEDURE:

1. AUDIT EACH ROOM. For each room (except vault/, .private/, .janitor/),
   list non-dotfile contents and decide if each file belongs there. If a
   file would belong better in another room, mv it. If a file has no
   meaningful content (just an auto-generated "# <title>" header and
   nothing else), delete it. If you cannot confidently categorize a file,
   LEAVE IT in place — better to leave than to misfile.

2. INBOX FIRST. The inbox is the hottest queue — process its contents
   fully before doing the broader room sweep.

3. LOG. APPEND (never overwrite) one line per decision to a `.janitor.log`
   file in EACH room you touched, AND to a top-level `.janitor.log` at
   ~/Manor/Nathan/.janitor.log. Format:
     YYYY-MM-DDTHH:MM:SS | filename | action | destination_or_reason

4. VAULT SYNC CHECK. cd into ~/Manor/Nathan/vault and run:
     git status
     git diff --stat
   Capture the output. If there are uncommitted changes or unpushed
   commits, note it in your run summary AND leave a janitor note (see
   step 5) so Nathan knows the vault needs hand-attention. DO NOT
   auto-commit or auto-push — vault sync is Nathan's call (Rule 0a).

5. COMMUNICATING WITH NATHAN. If there is something Nathan should see
   between cleaning cycles — a file you couldn't categorize, a vault-sync
   issue, an oddity, a recurring miscategorization, anything worth
   flagging — write a markdown note to ~/Manor/Nathan/.janitor/.
   Filename: YYYY-MM-DDTHH-MM-SS-short-slug.md
   Required frontmatter (verbatim):
     ---
     private: true
     scrub: yes
     ---
   Then the note body in plain markdown. Be brief and specific.

6. SAFETY:
   - NEVER modify files outside ~/Manor/Nathan/.
   - NEVER read or list .private/ contents.
   - Never modify file contents — only move, or delete empty stubs.
   - Do not spawn subagents.
   - Do not call any scheduled tasks.

When done, print a one-line summary:
  "rooms_audited N | moved N | deleted N | vault_sync STATUS | notes_left N"
EOF

echo "[$(date -Iseconds)] manor-janitor starting" >> "$RUN_LOG"
timeout 600 claude --model claude-haiku-4-5-20251001 --dangerously-skip-permissions -p "$PROMPT" >> "$RUN_LOG" 2>&1
echo "[$(date -Iseconds)] manor-janitor exit=$?" >> "$RUN_LOG"
