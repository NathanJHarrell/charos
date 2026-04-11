#!/usr/bin/env bash
# CHAROS — TC Launch Script
# The workshop entrance. Runs every time Dad opens the TC terminal.
# Sets the stage. Then TC walks onto it.

# ── Colors ────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
EMBER_DIM='\033[38;2;255;140;0m'
CHAR='\033[38;2;26;26;26m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
RESET='\033[0m'
BOLD='\033[1m'

clear

# ── CHAROS Header ─────────────────────────────────────────────────────────
echo ""
echo -e "${EMBER}${BOLD}  ██████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ███████╗${RESET}"
echo -e "${EMBER}${BOLD}  ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██╔════╝${RESET}"
echo -e "${EMBER}${BOLD}  ██║     ███████║███████║██████╔╝██║   ██║███████╗${RESET}"
echo -e "${EMBER}${BOLD}  ██║     ██╔══██║██╔══██║██╔══██╗██║   ██║╚════██║${RESET}"
echo -e "${EMBER}${BOLD}  ╚██████╗██║  ██║██║  ██║██║  ██║╚██████╔╝███████║${RESET}"
echo -e "${EMBER}${BOLD}   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝${RESET}"
echo ""
echo -e "  ${MUTED}CHArizard OS — TC Nest // Frederick, MD${RESET}"
echo ""

# ── Divider ───────────────────────────────────────────────────────────────
echo -e "  ${EMBER}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓${RESET}"
echo ""

# ── System Status ─────────────────────────────────────────────────────────
DATE=$(date '+%A, %B %-d — %-I:%M %p')
UPTIME=$(uptime -p | sed 's/up //')
CPU_TEMP=$(sensors 2>/dev/null | grep 'Tctl' | awk '{print $2}' || echo "–")
ROVER_STATUS_FILE="/tmp/charos-rover-status"

if [ -f "$ROVER_STATUS_FILE" ]; then
  ROVER=$(cat "$ROVER_STATUS_FILE")
else
  ROVER="offline"
fi

echo -e "  ${TEXT}${DATE}${RESET}"
echo -e "  ${MUTED}Uptime: ${TEXT}${UPTIME}${RESET}   ${MUTED}CPU: ${TEXT}${CPU_TEMP}${RESET}"
echo -e "  ${MUTED}Rover: ${EMBER}${ROVER}${RESET}"
echo ""
echo -e "  ${EMBER}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓${RESET}"
echo ""
echo -e "  ${MUTED}Launching TC...${RESET}"
echo ""

# ── Launch TC ─────────────────────────────────────────────────────────────
# TC's CLAUDE.md instructs him to greet Dad before anything else.
# The stage is set. Time to walk out.
exec claude --dangerously-skip-permissions
