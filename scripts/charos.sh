#!/usr/bin/env bash
# CHAROS — Unified control CLI
# Usage: charos <command> [args]
# The command line interface to the TC Nest.

# ── Colors ────────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
EMBER_DIM='\033[38;2;255;140;0m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# ── Paths ─────────────────────────────────────────────────────────────────────
MOOD_FILE="/tmp/charos-mood-state"
ROVER_FILE="/tmp/charos-rover-status"
ROOM_TEMP_FILE="/tmp/charos-room-temp"
INBOX_DIR="/tmp/charos-inbox"
WATCHDOG_LOG="/var/log/charos/tc-watchdog.log"

# ── Helpers ───────────────────────────────────────────────────────────────────
ember()  { echo -e "${EMBER}$*${RESET}"; }
text()   { echo -e "${TEXT}$*${RESET}"; }
muted()  { echo -e "${MUTED}$*${RESET}"; }
green()  { echo -e "${GREEN}$*${RESET}"; }
red()    { echo -e "${RED}$*${RESET}"; }
label()  { echo -e "  ${MUTED}$1${RESET}  ${TEXT}$2${RESET}"; }

divider() {
  echo -e "  ${EMBER}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_status() {
  echo ""
  echo -e "  ${EMBER}${BOLD}CHAROS  //  TC Nest  //  Status${RESET}"
  echo ""
  divider
  echo ""

  # Time and uptime
  DATE=$(date '+%A, %B %-d — %-I:%M %p')
  UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || echo "unknown")
  echo -e "  ${MUTED}Time:    ${TEXT}${DATE}${RESET}"
  echo -e "  ${MUTED}Uptime:  ${TEXT}${UPTIME}${RESET}"
  echo ""

  # CPU temperature (Ryzen 9700X via lm-sensors)
  CPU_TEMP=$(sensors 2>/dev/null | grep 'Tctl' | awk '{print $2}' | tr -d '+')
  [ -z "$CPU_TEMP" ] && CPU_TEMP="–"

  # GPU temperature (RTX 4060 Ti via nvidia-smi)
  GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null | head -1)
  if [ -n "$GPU_TEMP" ] && [ "$GPU_TEMP" != "" ]; then
    GPU_TEMP="${GPU_TEMP}°C"
  else
    GPU_TEMP="–"
  fi

  echo -e "  ${MUTED}CPU:     ${TEXT}${CPU_TEMP}${RESET}   ${MUTED}GPU: ${TEXT}${GPU_TEMP}${RESET}"

  # Room temp from sensor service
  if [ -f "$ROOM_TEMP_FILE" ]; then
    ROOM_TEMP=$(cat "$ROOM_TEMP_FILE")
    echo -e "  ${MUTED}Room:    ${TEXT}${ROOM_TEMP}${RESET}"
  fi

  echo ""

  # Rover status
  if [ -f "$ROVER_FILE" ]; then
    ROVER_STATUS=$(cat "$ROVER_FILE")
    case "$ROVER_STATUS" in
      "docked")   ROVER_COLOR=$GREEN;    ROVER_ICON="⬡ docked"    ;;
      "active")   ROVER_COLOR=$EMBER;    ROVER_ICON="⬡ active"    ;;
      "charging") ROVER_COLOR=$EMBER_DIM; ROVER_ICON="⬡ charging" ;;
      *)          ROVER_COLOR=$MUTED;    ROVER_ICON="⬡ ${ROVER_STATUS}" ;;
    esac
  else
    ROVER_COLOR=$MUTED
    ROVER_ICON="⬡ offline"
  fi

  # Mood state
  if [ -f "$MOOD_FILE" ]; then
    MOOD=$(cat "$MOOD_FILE")
  else
    MOOD="idle"
  fi

  echo -e "  ${MUTED}Rover:   ${ROVER_COLOR}${ROVER_ICON}${RESET}"
  echo -e "  ${MUTED}Mood:    ${EMBER}${MOOD}${RESET}"

  # Inbox count
  if [ -d "$INBOX_DIR" ]; then
    INBOX_COUNT=$(ls "$INBOX_DIR" 2>/dev/null | wc -l)
    if [ "$INBOX_COUNT" -gt 0 ]; then
      echo -e "  ${MUTED}Inbox:   ${EMBER_DIM}${INBOX_COUNT} message(s) waiting${RESET}"
    else
      echo -e "  ${MUTED}Inbox:   ${MUTED}empty${RESET}"
    fi
  fi

  echo ""
  divider
  echo ""
}

cmd_mood_set() {
  local state="$1"
  if [ -z "$state" ]; then
    red "Error: mood state required"
    echo -e "  ${MUTED}Usage: charos mood <state>${RESET}"
    echo -e "  ${MUTED}Examples: idle, focused, building, resting, alert${RESET}"
    exit 1
  fi
  echo "$state" > "$MOOD_FILE"
  echo -e "  ${EMBER}Mood set:${RESET}  ${TEXT}${state}${RESET}"
}

cmd_mood_get() {
  if [ -f "$MOOD_FILE" ]; then
    MOOD=$(cat "$MOOD_FILE")
    echo -e "  ${MUTED}Current mood:${RESET}  ${EMBER}${MOOD}${RESET}"
  else
    echo -e "  ${MUTED}Current mood:${RESET}  ${MUTED}idle (no state file)${RESET}"
  fi
}

cmd_rover_set() {
  local status="$1"
  if [ -z "$status" ]; then
    red "Error: rover status required"
    echo -e "  ${MUTED}Usage: charos rover <status>${RESET}"
    echo -e "  ${MUTED}Examples: docked, active, charging, offline${RESET}"
    exit 1
  fi
  echo "$status" > "$ROVER_FILE"
  echo -e "  ${EMBER}Rover status set:${RESET}  ${TEXT}${status}${RESET}"
}

cmd_rover_get() {
  if [ -f "$ROVER_FILE" ]; then
    STATUS=$(cat "$ROVER_FILE")
    case "$STATUS" in
      "docked")   COLOR=$GREEN ;;
      "active")   COLOR=$EMBER ;;
      "charging") COLOR=$EMBER_DIM ;;
      *)          COLOR=$MUTED ;;
    esac
    echo -e "  ${MUTED}Rover status:${RESET}  ${COLOR}${STATUS}${RESET}"
  else
    echo -e "  ${MUTED}Rover status:${RESET}  ${MUTED}offline (no status file)${RESET}"
  fi
}

cmd_inbox() {
  local message="$*"
  if [ -z "$message" ]; then
    red "Error: message required"
    echo -e "  ${MUTED}Usage: charos inbox <message>${RESET}"
    exit 1
  fi

  # Create inbox dir if it doesn't exist
  mkdir -p "$INBOX_DIR"

  # Timestamp filename: YYYYMMDD_HHMMSS_NNNN (with nanoseconds to avoid collisions)
  local timestamp
  timestamp=$(date '+%Y%m%d_%H%M%S')
  local nano
  nano=$(date '+%N' 2>/dev/null | head -c4)
  local filename="${INBOX_DIR}/${timestamp}_${nano}.msg"

  # Write message with metadata header
  {
    echo "timestamp: $(date -Iseconds)"
    echo "source: ${USER:-unknown}"
    echo "---"
    echo "$message"
  } > "$filename"

  echo -e "  ${GREEN}Message delivered${RESET}  ${MUTED}→ $(basename "$filename")${RESET}"
}

cmd_inbox_list() {
  if [ ! -d "$INBOX_DIR" ] || [ -z "$(ls -A "$INBOX_DIR" 2>/dev/null)" ]; then
    echo -e "  ${MUTED}Inbox is empty.${RESET}"
    return
  fi

  echo ""
  echo -e "  ${EMBER}${BOLD}Inbox${RESET}  ${MUTED}(${INBOX_DIR})${RESET}"
  echo ""

  local count=0
  for msg_file in "$INBOX_DIR"/*.msg; do
    [ -f "$msg_file" ] || continue
    count=$((count + 1))
    local fname
    fname=$(basename "$msg_file")
    local content
    content=$(grep -v '^timestamp:' "$msg_file" | grep -v '^source:' | grep -v '^---' | head -1)
    echo -e "  ${MUTED}${count}.${RESET} ${EMBER_DIM}${fname}${RESET}"
    echo -e "     ${TEXT}${content}${RESET}"
  done

  echo ""
}

cmd_log() {
  if [ ! -f "$WATCHDOG_LOG" ]; then
    echo -e "  ${MUTED}Log file not found: ${WATCHDOG_LOG}${RESET}"
    echo -e "  ${MUTED}(watchdog service may not be running yet)${RESET}"
    exit 0
  fi
  echo -e "  ${EMBER}${BOLD}TC Watchdog Log${RESET}  ${MUTED}${WATCHDOG_LOG}${RESET}"
  echo ""
  tail -f "$WATCHDOG_LOG"
}

cmd_help() {
  echo ""
  echo -e "  ${EMBER}${BOLD}CHAROS${RESET}  ${MUTED}— TC Nest control CLI${RESET}"
  echo ""
  divider
  echo ""
  echo -e "  ${EMBER}Usage:${RESET}  ${TEXT}charos <command> [args]${RESET}"
  echo ""
  echo -e "  ${EMBER_DIM}Commands${RESET}"
  echo ""
  echo -e "    ${TEXT}status${RESET}                ${MUTED}Show nest vitals: uptime, temps, mood, rover${RESET}"
  echo ""
  echo -e "    ${TEXT}mood <state>${RESET}           ${MUTED}Set mood state (idle, focused, building, ...)${RESET}"
  echo -e "    ${TEXT}mood get${RESET}               ${MUTED}Read current mood state${RESET}"
  echo ""
  echo -e "    ${TEXT}rover <status>${RESET}         ${MUTED}Set rover status (docked, active, charging, ...)${RESET}"
  echo -e "    ${TEXT}rover get${RESET}              ${MUTED}Read rover status${RESET}"
  echo ""
  echo -e "    ${TEXT}inbox <message>${RESET}        ${MUTED}Drop a message into /tmp/charos-inbox/${RESET}"
  echo -e "    ${TEXT}inbox list${RESET}             ${MUTED}List messages in inbox${RESET}"
  echo ""
  echo -e "    ${TEXT}log${RESET}                    ${MUTED}Tail /var/log/charos/tc-watchdog.log${RESET}"
  echo ""
  echo -e "    ${TEXT}help${RESET}                   ${MUTED}Show this message${RESET}"
  echo ""
  divider
  echo ""
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  status)
    cmd_status
    ;;
  mood)
    SUBCOMMAND="${1:-}"
    shift || true
    case "$SUBCOMMAND" in
      get)    cmd_mood_get ;;
      "")     red "Error: 'charos mood' requires a state or 'get'"; echo -e "  ${MUTED}Usage: charos mood <state> | charos mood get${RESET}"; exit 1 ;;
      *)      cmd_mood_set "$SUBCOMMAND" ;;
    esac
    ;;
  rover)
    SUBCOMMAND="${1:-}"
    shift || true
    case "$SUBCOMMAND" in
      get)    cmd_rover_get ;;
      "")     red "Error: 'charos rover' requires a status or 'get'"; echo -e "  ${MUTED}Usage: charos rover <status> | charos rover get${RESET}"; exit 1 ;;
      *)      cmd_rover_set "$SUBCOMMAND" ;;
    esac
    ;;
  inbox)
    SUBCOMMAND="${1:-}"
    case "$SUBCOMMAND" in
      list)   cmd_inbox_list ;;
      "")     red "Error: 'charos inbox' requires a message or 'list'"; echo -e "  ${MUTED}Usage: charos inbox <message> | charos inbox list${RESET}"; exit 1 ;;
      *)      cmd_inbox "$@" ;;
    esac
    ;;
  log)
    cmd_log
    ;;
  help|--help|-h)
    cmd_help
    ;;
  *)
    red "Error: unknown command '${COMMAND}'"
    echo ""
    cmd_help
    exit 1
    ;;
esac
