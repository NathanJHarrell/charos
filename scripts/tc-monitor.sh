#!/usr/bin/env bash
# CHAROS — TC Monitor Script
# Full environment health scan. TC runs this to see the state of his own world.
# Checks Forge, services, disk, load, memory, git, inbox, and watchdog activity.
#
# NOTE: This file needs chmod +x — NixOS activation handles this in production.

# ── Source environment ────────────────────────────────────────────────────────
CHAROS_ENV_FILE="${CHAROS_HOME:-/home/nathan/.charos}/shell/charos-env.sh"
if [ -f "$CHAROS_ENV_FILE" ]; then
  # shellcheck source=/dev/null
  source "$CHAROS_ENV_FILE"
fi

# ── Source signal functions ───────────────────────────────────────────────────
SIGNAL_SCRIPT="${CHAROS_HOME:-/home/nathan/.charos}/scripts/tc-signal.sh"
if [ -f "$SIGNAL_SCRIPT" ]; then
  # shellcheck source=/dev/null
  source "$SIGNAL_SCRIPT"
fi

# Fallbacks
FORGE_PORT="${FORGE_PORT:-3001}"
TC_INBOX="${TC_INBOX:-/tmp/charos-inbox}"
TC_LOG_DIR="${TC_LOG_DIR:-/var/log/charos}"
WATCHDOG_LOG="${TC_LOG_DIR}/tc-watchdog.log"

# ── Colors ────────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
EMBER_DIM='\033[38;2;255;140;0m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
AMBER='\033[38;2;255;140;0m'
RESET='\033[0m'
BOLD='\033[1m'

# ── Status tracking ───────────────────────────────────────────────────────────
CRITICAL_COUNT=0
NOTABLE_COUNT=0
CRITICAL_MESSAGES=()

# ── Status line helpers ───────────────────────────────────────────────────────
ok()       { echo -e "  ${GREEN}✓${RESET}  ${MUTED}$1${RESET}  ${TEXT}$2${RESET}"; }
notable()  { echo -e "  ${AMBER}⚠${RESET}  ${MUTED}$1${RESET}  ${AMBER}$2${RESET}"; NOTABLE_COUNT=$((NOTABLE_COUNT + 1)); }
critical() { echo -e "  ${RED}✗${RESET}  ${MUTED}$1${RESET}  ${RED}$2${RESET}"; CRITICAL_COUNT=$((CRITICAL_COUNT + 1)); CRITICAL_MESSAGES+=("$1: $2"); }

divider() {
  echo -e "  ${EMBER}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${EMBER}${BOLD}CHAROS  //  TC Monitor${RESET}  ${MUTED}$(date '+%A, %B %-d — %-I:%M %p')${RESET}"
echo ""
divider
echo ""

# ── 1. Forge ──────────────────────────────────────────────────────────────────
FORGE_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
  "http://localhost:${FORGE_PORT}" \
  --max-time 3 2>/dev/null)

if [ "$FORGE_STATUS" = "200" ]; then
  ok "Forge" "healthy  (HTTP ${FORGE_STATUS} on :${FORGE_PORT})"
else
  critical "Forge" "DOWN  (HTTP ${FORGE_STATUS:-no response} on :${FORGE_PORT})"
fi

# ── 2. tc-mood service ────────────────────────────────────────────────────────
MOOD_STATE=$(systemctl is-active tc-mood 2>/dev/null)
case "$MOOD_STATE" in
  active)   ok "tc-mood" "active" ;;
  inactive) notable "tc-mood" "inactive" ;;
  *)        critical "tc-mood" "${MOOD_STATE:-not found}" ;;
esac

# ── 3. tc-watchdog service ────────────────────────────────────────────────────
WATCHDOG_STATE=$(systemctl is-active tc-watchdog 2>/dev/null)
case "$WATCHDOG_STATE" in
  active)   ok "tc-watchdog" "active" ;;
  inactive) notable "tc-watchdog" "inactive" ;;
  *)        critical "tc-watchdog" "${WATCHDOG_STATE:-not found}" ;;
esac

# ── 4. Disk space (/) ────────────────────────────────────────────────────────
DISK_USED_PCT=$(df / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
DISK_HUMAN=$(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 " used)"}')

if [ "$DISK_USED_PCT" -ge 90 ] 2>/dev/null; then
  critical "Disk (/)" "${DISK_HUMAN}"
elif [ "$DISK_USED_PCT" -ge 80 ] 2>/dev/null; then
  notable "Disk (/)" "${DISK_HUMAN}"
else
  ok "Disk (/)" "${DISK_HUMAN}"
fi

# ── 5. System load ────────────────────────────────────────────────────────────
# /proc/loadavg: 1min 5min 15min running/total lastpid
LOAD_1MIN=$(awk '{print $1}' /proc/loadavg 2>/dev/null)
LOAD_ALL=$(awk '{print $1 "  " $2 "  " $3}' /proc/loadavg 2>/dev/null)

# bc comparison for float: flag if 1min load > 8.0 (8 cores)
LOAD_HIGH=$(echo "$LOAD_1MIN > 8.0" | bc -l 2>/dev/null)
LOAD_NOTABLE=$(echo "$LOAD_1MIN > 6.0" | bc -l 2>/dev/null)

if [ "$LOAD_HIGH" = "1" ]; then
  critical "Load" "${LOAD_ALL}  (1m/5m/15m)"
elif [ "$LOAD_NOTABLE" = "1" ]; then
  notable "Load" "${LOAD_ALL}  (1m/5m/15m)"
else
  ok "Load" "${LOAD_ALL}  (1m/5m/15m)"
fi

# ── 6. Memory ────────────────────────────────────────────────────────────────
# Parse free output for used/total, compute % used
MEM_TOTAL=$(free -b | awk 'NR==2 {print $2}')
MEM_USED=$(free -b  | awk 'NR==2 {print $3}')
MEM_HUMAN=$(free -h | awk 'NR==2 {print $3 " / " $2}')

if [ -n "$MEM_TOTAL" ] && [ "$MEM_TOTAL" -gt 0 ] 2>/dev/null; then
  MEM_PCT=$(( MEM_USED * 100 / MEM_TOTAL ))
  MEM_LABEL="${MEM_HUMAN}  (${MEM_PCT}%)"
  if [ "$MEM_PCT" -ge 90 ]; then
    critical "Memory" "$MEM_LABEL"
  elif [ "$MEM_PCT" -ge 75 ]; then
    notable "Memory" "$MEM_LABEL"
  else
    ok "Memory" "$MEM_LABEL"
  fi
else
  notable "Memory" "could not parse free output"
fi

# ── 7. CHAROS git — updates available? ───────────────────────────────────────
CHAROS_REPO="${CHAROS_HOME:-/home/nathan/.charos}"
if [ -d "${CHAROS_REPO}/.git" ]; then
  # Fetch quietly, then check if remote is ahead
  git -C "$CHAROS_REPO" fetch origin --quiet 2>/dev/null
  BEHIND=$(git -C "$CHAROS_REPO" rev-list HEAD..origin/main --count 2>/dev/null)
  if [ -z "$BEHIND" ] || [ "$BEHIND" = "0" ]; then
    ok "CHAROS git" "up to date"
  else
    notable "CHAROS git" "${BEHIND} commit(s) behind origin/main"
  fi
else
  notable "CHAROS git" "repo not found at ${CHAROS_REPO}"
fi

# ── 8. Inbox ─────────────────────────────────────────────────────────────────
if [ -d "$TC_INBOX" ]; then
  INBOX_COUNT=$(ls "$TC_INBOX" 2>/dev/null | wc -l)
  if [ "$INBOX_COUNT" -eq 0 ]; then
    ok "Inbox" "empty"
  elif [ "$INBOX_COUNT" -le 3 ]; then
    notable "Inbox" "${INBOX_COUNT} unprocessed message(s)"
  else
    critical "Inbox" "${INBOX_COUNT} messages waiting — something needs attention"
  fi
else
  ok "Inbox" "empty  (no inbox dir)"
fi

# ── 9. Last watchdog activity ─────────────────────────────────────────────────
if [ -f "$WATCHDOG_LOG" ]; then
  LAST_LINE=$(tail -1 "$WATCHDOG_LOG" 2>/dev/null)
  if [ -n "$LAST_LINE" ]; then
    ok "Watchdog log" "${LAST_LINE}"
  else
    notable "Watchdog log" "exists but empty"
  fi
else
  notable "Watchdog log" "no log found at ${WATCHDOG_LOG}"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
divider
echo ""

if [ "$CRITICAL_COUNT" -gt 0 ]; then
  echo -e "  ${RED}${BOLD}CRITICAL${RESET}  ${TEXT}${CRITICAL_COUNT} issue(s) need attention${RESET}"
  for msg in "${CRITICAL_MESSAGES[@]}"; do
    echo -e "  ${MUTED}→${RESET}  ${RED}${msg}${RESET}"
  done
  echo ""

  # Escalate to Dad if signal script is available
  if command -v escalate_to_dad &>/dev/null 2>&1 || [ -f "$SIGNAL_SCRIPT" ]; then
    ESCALATION_MSG="${CRITICAL_COUNT} critical issue(s): ${CRITICAL_MESSAGES[0]}"
    if [ "$CRITICAL_COUNT" -gt 1 ]; then
      ESCALATION_MSG="${CRITICAL_COUNT} critical issues — run charos monitor"
    fi
    escalate_to_dad "$ESCALATION_MSG" "critical" 2>/dev/null || true
  fi

elif [ "$NOTABLE_COUNT" -gt 0 ]; then
  echo -e "  ${AMBER}${BOLD}NOTABLE${RESET}  ${TEXT}${NOTABLE_COUNT} item(s) worth a look${RESET}"
  echo ""

else
  echo -e "  ${GREEN}${BOLD}ALL CLEAR${RESET}  ${TEXT}Everything looks good.${RESET}"
  echo ""
fi
