#!/usr/bin/env bash
# CHAROS — Forge Health Monitor
# Checks if Forge is alive. Tries to heal it. Escalates to TC if it can't.
# Runs on a systemd timer every 5 minutes.

# ── Config ────────────────────────────────────────────────────────────────────
CHAROS_HOME="/home/nathan/.charos"

# Source env (FORGE_PORT, FORGE_DIR, TC_INBOX, etc.)
[ -f "$CHAROS_HOME/shell/charos-env.sh" ] && source "$CHAROS_HOME/shell/charos-env.sh"

FORGE_PORT="${FORGE_PORT:-3001}"
FORGE_DIR="${FORGE_DIR:-/home/nathan/forge}"
TC_INBOX="${TC_INBOX:-/tmp/charos-inbox}"
TC_LOG_DIR="${TC_LOG_DIR:-/var/log/charos}"
LOG_FILE="$TC_LOG_DIR/forge-monitor.log"

# State file — tracks whether forge was already known-down to avoid inbox spam
STATE_FILE="/tmp/charos-forge-state"

# ── Logging ──────────────────────────────────────────────────────────────────
log() {
  local level="$1"; shift
  echo "[$(date -Iseconds)] [$level] $*" >> "$LOG_FILE"
}

# ── Signal / Inbox helpers ────────────────────────────────────────────────────
drop_inbox() {
  local severity="$1"
  local source="$2"
  local message="$3"
  mkdir -p "$TC_INBOX"
  local ts; ts=$(date '+%Y%m%d_%H%M%S')
  local nano; nano=$(date '+%N' 2>/dev/null | head -c4)
  cat > "$TC_INBOX/${ts}_${nano}.msg" <<EOF
SEVERITY=${severity}
SOURCE=${source}
---
${message}
EOF
}

# ── Health check ──────────────────────────────────────────────────────────────
check_forge() {
  local http_status
  http_status=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 --max-time 10 \
    "http://localhost:${FORGE_PORT}" 2>/dev/null)

  if [ "$http_status" = "200" ] || [ "$http_status" = "304" ]; then
    return 0  # healthy
  else
    return 1  # down
  fi
}

# ── Restart attempt ───────────────────────────────────────────────────────────
restart_forge() {
  log "INFO" "Attempting Forge restart via systemctl..."

  if systemctl --user restart forge 2>/dev/null; then
    log "INFO" "systemctl restart succeeded, waiting 10s for startup..."
    sleep 10
    if check_forge; then
      log "INFO" "Forge recovered after systemctl restart."
      return 0
    fi
  fi

  # Fallback: try killing stale next process and restarting manually
  log "WARN" "systemctl restart failed or service not found, trying manual restart..."
  pkill -f "next dev.*3001" 2>/dev/null || true
  sleep 2

  if [ -d "$FORGE_DIR" ]; then
    cd "$FORGE_DIR" || return 1
    nohup npm run dev -- --port "$FORGE_PORT" >> "$TC_LOG_DIR/forge-dev.log" 2>&1 &
    disown
    log "INFO" "Manual restart launched (pid $!), waiting 15s..."
    sleep 15
    if check_forge; then
      log "INFO" "Forge recovered after manual restart."
      return 0
    fi
  fi

  return 1  # couldn't recover
}

# ── Main ──────────────────────────────────────────────────────────────────────
mkdir -p "$TC_LOG_DIR"

if check_forge; then
  # Forge is healthy
  if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" = "down" ]; then
    # Was down, now recovered — notify TC
    log "INFO" "Forge recovered. Was previously down."
    echo "healthy" > "$STATE_FILE"
    drop_inbox "routine" "forge-monitor" \
      "Forge has recovered and is responding on port ${FORGE_PORT}. No action needed."
  else
    # All good, routine heartbeat
    echo "healthy" > "$STATE_FILE"
    log "INFO" "Forge healthy on port ${FORGE_PORT}."
  fi
else
  # Forge is down
  log "WARN" "Forge not responding on port ${FORGE_PORT}. Attempting recovery..."

  if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" = "down" ]; then
    # Already knew it was down — still down, don't spam inbox
    log "WARN" "Forge still down (previously known). Skipping duplicate alert."
    # Still try to restart
    restart_forge || true
    exit 0
  fi

  # First time detecting this outage
  echo "down" > "$STATE_FILE"

  if restart_forge; then
    # Auto-healed
    echo "healthy" > "$STATE_FILE"
    log "INFO" "Forge auto-healed. Dropping routine recovery note to inbox."
    drop_inbox "routine" "forge-monitor" \
      "Forge was down on port ${FORGE_PORT} but I restarted it automatically. It's back up."
  else
    # Can't recover — wake TC
    log "ERROR" "Forge is down and auto-restart failed. Escalating to TC."
    drop_inbox "critical" "forge-monitor" \
      "Forge is DOWN on port ${FORGE_PORT} and I could not restart it automatically.

Diagnosis needed:
- Check process: ps aux | grep next
- Check logs: tail -50 ${TC_LOG_DIR}/forge-dev.log
- Check directory: ls -la ${FORGE_DIR}
- Manual restart: cd ${FORGE_DIR} && npm run dev -- --port ${FORGE_PORT}

Last known state file: ${STATE_FILE}"
  fi
fi
