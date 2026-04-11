#!/usr/bin/env bash
# CHAROS — TC Launch Script
# The workshop entrance. Runs every time the nest wakes up.
# Sets the stage. Then TC walks onto it and greets Dad.

# ── Colors ────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
EMBER_DIM='\033[38;2;255;140;0m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
RESET='\033[0m'
BOLD='\033[1m'

clear

# ── CHAROS ASCII Header ───────────────────────────────────────────────────
echo ""
echo -e "${EMBER}${BOLD}  ██████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ███████╗${RESET}"
echo -e "${EMBER}${BOLD}  ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██╔════╝${RESET}"
echo -e "${EMBER}${BOLD}  ██║     ███████║███████║██████╔╝██║   ██║███████╗${RESET}"
echo -e "${EMBER}${BOLD}  ██║     ██╔══██║██╔══██║██╔══██╗██║   ██║╚════██║${RESET}"
echo -e "${EMBER}${BOLD}  ╚██████╗██║  ██║██║  ██║██║  ██║╚██████╔╝███████║${RESET}"
echo -e "${EMBER}${BOLD}   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝${RESET}"
echo ""
echo -e "  ${MUTED}CHArizard OS  //  TC Nest  //  Frederick, MD${RESET}"
echo ""

# ── Flame divider ─────────────────────────────────────────────────────────
echo -e "  ${EMBER}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ── System Vitals ─────────────────────────────────────────────────────────
DATE=$(date '+%A, %B %-d — %-I:%M %p')
UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || echo "just started")

# CPU temperature (Ryzen 9700X via lm-sensors)
CPU_TEMP=$(sensors 2>/dev/null | grep 'Tctl' | awk '{print $2}' | tr -d '+' || echo "–")

# GPU temperature (RTX 4060 Ti via nvidia-smi)
GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null | head -1 || echo "–")
[ -n "$GPU_TEMP" ] && GPU_TEMP="${GPU_TEMP}°C"

# Room temp from BME680 if mood engine is running
ROOM_TEMP_FILE="/tmp/charos-room-temp"
if [ -f "$ROOM_TEMP_FILE" ]; then
  ROOM_TEMP=$(cat "$ROOM_TEMP_FILE")
  ROOM_LINE="  ${MUTED}Room:   ${TEXT}${ROOM_TEMP}${RESET}"
fi

# Rover status
ROVER_FILE="/tmp/charos-rover-status"
if [ -f "$ROVER_FILE" ]; then
  ROVER_STATUS=$(cat "$ROVER_FILE")
  case "$ROVER_STATUS" in
    "docked")   ROVER_COLOR=$GREEN;  ROVER_ICON="⬡ docked"    ;;
    "active")   ROVER_COLOR=$EMBER;  ROVER_ICON="⬡ active 🔥" ;;
    "charging") ROVER_COLOR=$EMBER_DIM; ROVER_ICON="⬡ charging" ;;
    *)          ROVER_COLOR=$MUTED;  ROVER_ICON="⬡ offline"   ;;
  esac
else
  ROVER_COLOR=$MUTED
  ROVER_ICON="⬡ offline"
fi

# Mood engine status
MOOD_FILE="/tmp/charos-mood-state"
if [ -f "$MOOD_FILE" ]; then
  MOOD=$(cat "$MOOD_FILE")
else
  MOOD="idle"
fi

echo -e "  ${TEXT}${DATE}${RESET}"
echo -e "  ${MUTED}Uptime:  ${TEXT}${UPTIME}${RESET}"
echo -e "  ${MUTED}CPU:     ${TEXT}${CPU_TEMP}${RESET}   ${MUTED}GPU: ${TEXT}${GPU_TEMP}${RESET}"
[ -n "$ROOM_LINE" ] && echo -e "$ROOM_LINE"
echo -e "  ${MUTED}Rover:   ${ROVER_COLOR}${ROVER_ICON}${RESET}"
echo -e "  ${MUTED}Mood:    ${EMBER}${MOOD}${RESET}"
echo ""

# ── Flame divider ─────────────────────────────────────────────────────────
echo -e "  ${EMBER}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${MUTED}TC is waking up...${RESET}"
echo ""

# ── Small dramatic pause ───────────────────────────────────────────────────
sleep 0.4

# ── Hand off to TC ────────────────────────────────────────────────────────
# TC's CLAUDE.md at /home/nathan/.charos/claude/CLAUDE.md
# instructs him to greet Dad the moment the session starts.
# The stage is set. Time to walk out.
exec claude --dangerously-skip-permissions
