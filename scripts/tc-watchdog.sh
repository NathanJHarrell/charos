#!/run/current-system/sw/bin/bash
# CHAROS — TC Watchdog
# The autonomy layer. Watches for events and wakes TC to handle them.
# Runs as a systemd service on the nest.
#
# Architecture:
#   Any service drops a .msg file into /tmp/charos-inbox/
#   Watchdog picks it up, decides severity, wakes TC if needed
#   TC reads the message and acts on it
#   Handled messages move to /tmp/charos-inbox/processed/

# ── Config ────────────────────────────────────────────────────────────────────
INBOX_DIR="/tmp/charos-inbox"
PROCESSED_DIR="/tmp/charos-inbox/processed"
LOG_DIR="/var/log/charos"
LOG_FILE="$LOG_DIR/tc-watchdog.log"
CLAUDE_HOME="${HOME}/.charos/claude"
WATCHDOG_CONTEXT="$CLAUDE_HOME/CLAUDE.md"

# How TC gets woken: claude -p with the message as prompt
# --continue keeps a persistent session alive across invocations
TC_CMD="claude --dangerously-skip-permissions -p"

# ── Setup ─────────────────────────────────────────────────────────────────────
mkdir -p "$INBOX_DIR" "$PROCESSED_DIR"
mkdir -p "$LOG_DIR"

# ── Logging ──────────────────────────────────────────────────────────────────
log() {
  local level="$1"
  shift
  echo "[$(date -Iseconds)] [$level] $*" >> "$LOG_FILE"
}

log "INFO" "TC Watchdog started. Watching $INBOX_DIR"

# ── Severity parser ───────────────────────────────────────────────────────────
# Message format:
#   SEVERITY=routine|notable|critical
#   SOURCE=<service-name>
#   ---
#   <message body>
#
# If no SEVERITY header, defaults to routine.

parse_severity() {
  local file="$1"
  local severity
  severity=$(grep '^SEVERITY=' "$file" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '[:space:]')
  echo "${severity:-routine}"
}

parse_source() {
  local file="$1"
  local source
  source=$(grep '^SOURCE=' "$file" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '[:space:]')
  # Also check 'source:' (lowercase, from charos inbox command)
  [ -z "$source" ] && source=$(grep '^source:' "$file" 2>/dev/null | head -1 | sed 's/^source: //' | tr -d '[:space:]')
  echo "${source:-unknown}"
}

parse_body() {
  local file="$1"
  # Everything after the --- separator
  sed -n '/^---/,$ p' "$file" | tail -n +2
}

# ── LED signal ────────────────────────────────────────────────────────────────
# Signal TC's mood engine to pulse for attention
signal_leds() {
  local severity="$1"
  case "$severity" in
    critical) echo "alert"   > /tmp/charos-mood-state ;;
    notable)  echo "notable" > /tmp/charos-mood-state ;;
    routine)  ;; # silent
  esac
}

# ── Handle message ────────────────────────────────────────────────────────────
handle_message() {
  local file="$1"
  local filename
  filename=$(basename "$file")

  local severity source body
  severity=$(parse_severity "$file")
  source=$(parse_source "$file")
  body=$(parse_body "$file")

  log "INFO" "Processing: $filename | severity=$severity | source=$source"

  # Signal LEDs based on severity
  signal_leds "$severity"

  # Build prompt for TC
  local prompt
  prompt=$(cat <<EOF
[WATCHDOG EVENT]
Source: $source
Severity: $severity
Time: $(date '+%A, %B %-d at %-I:%M %p')

$body

Handle this appropriately. For routine events, log what you did. For notable or critical events, diagnose and fix if possible, then write a summary to $LOG_FILE.
EOF
)

  # Wake TC
  if [ "$severity" = "routine" ]; then
    # Routine: fire and forget, don't wait
    $TC_CMD "$prompt" >> "$LOG_FILE" 2>&1 &
    log "INFO" "TC woken (routine, async) for: $source"
  else
    # Notable/critical: wait for TC to finish, log result
    log "INFO" "TC woken ($severity, sync) for: $source"
    $TC_CMD "$prompt" >> "$LOG_FILE" 2>&1
    log "INFO" "TC handled $severity event from $source"
  fi

  # Move to processed
  mv "$file" "$PROCESSED_DIR/$filename"
  log "INFO" "Message archived: $filename"
}

# ── Watch loop ────────────────────────────────────────────────────────────────
# inotifywait is preferred (event-driven), but we fall back to polling
# if inotify-tools isn't available yet

if command -v inotifywait &>/dev/null; then
  log "INFO" "Using inotifywait (event-driven mode)"

  inotifywait -m -e close_write --format '%f' "$INBOX_DIR" 2>/dev/null | while read -r filename; do
    # Only process .msg files, not processed/ directory events
    if [[ "$filename" == *.msg ]]; then
      filepath="$INBOX_DIR/$filename"
      if [ -f "$filepath" ]; then
        handle_message "$filepath"
      fi
    fi
  done

else
  log "WARN" "inotifywait not found — using polling mode (5s interval)"
  log "WARN" "Install inotify-tools for event-driven mode"

  while true; do
    for msg_file in "$INBOX_DIR"/*.msg; do
      [ -f "$msg_file" ] || continue
      handle_message "$msg_file"
    done
    sleep 5
  done
fi
