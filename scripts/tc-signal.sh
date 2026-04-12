#!/usr/bin/env bash
# CHAROS — TC Signal Script
# How TC reaches Dad through light.
# Workstation LEDs → wait → bedroom panel if no ack.
#
# NOTE: This file needs chmod +x — NixOS activation handles this in production.

# ── Source environment ────────────────────────────────────────────────────────
CHAROS_ENV_FILE="${CHAROS_HOME:-/home/nathan/.charos}/shell/charos-env.sh"
if [ -f "$CHAROS_ENV_FILE" ]; then
  # shellcheck source=/dev/null
  source "$CHAROS_ENV_FILE"
fi

# Fallback values if env not sourced
WLED_WORKSTATION="${WLED_WORKSTATION:-http://192.168.1.200}"
WLED_BEDROOM="${WLED_BEDROOM:-http://192.168.1.201}"
OPENRGB_HOST="${OPENRGB_HOST:-localhost}"
OPENRGB_PORT="${OPENRGB_PORT:-6800}"
TC_ACK_FILE="${TC_ACK_FILE:-/tmp/charos-ack}"
TC_SIGNAL_STATE="${TC_SIGNAL_STATE:-/tmp/charos-signal-state}"
TC_LOG_DIR="${TC_LOG_DIR:-/var/log/charos}"
SIGNAL_LOG="${TC_LOG_DIR}/tc-signal.log"

# ── Colors (terminal output) ──────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
EMBER_DIM='\033[38;2;255;140;0m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
RESET='\033[0m'
BOLD='\033[1m'

# ── LED color values (WLED JSON hex, no #) ────────────────────────────────────
COLOR_EMBER="FF5900"    # Normal TC color — warm presence
COLOR_ALERT="FF2200"    # Critical — TC needs you NOW
COLOR_NOTABLE="FF8C00"  # Hey, look at this when you can
COLOR_GREEN="66CC88"    # Good / recovery
COLOR_OFF="000000"      # Dark

# ── Logging ───────────────────────────────────────────────────────────────────
_log() {
  local level="$1"
  shift
  local msg="$*"
  local ts
  ts=$(date -Iseconds)
  mkdir -p "$TC_LOG_DIR"
  echo "${ts}  [${level}]  ${msg}" >> "$SIGNAL_LOG"
}

# ── WLED helpers ──────────────────────────────────────────────────────────────
# _wled_send <base_url> <json_payload>
# Posts a WLED JSON API state update. Silent on failure — LEDs are nice-to-have.
_wled_send() {
  local url="$1"
  local payload="$2"
  if curl -sf -X POST \
       -H "Content-Type: application/json" \
       -d "$payload" \
       "${url}/json/state" \
       --max-time 3 \
       > /dev/null 2>&1; then
    return 0
  else
    _log "WARN" "WLED unreachable: ${url} (hardware may not be installed yet)"
    return 1
  fi
}

# ── signal_workstation <severity> ─────────────────────────────────────────────
# Drives the WS2812B strips at Nathan's workstation.
#   routine  → nothing (silent, don't interrupt the vibe)
#   notable  → slow amber pulse (hey, when you have a sec)
#   critical → fast red pulse (TC needs you NOW)
#   clear    → return to ember idle
signal_workstation() {
  local severity="${1:-routine}"

  case "$severity" in
    routine)
      # Intentionally silent — don't interrupt focused work for routine events
      _log "DEBUG" "signal_workstation: routine — no LED change"
      return 0
      ;;
    notable)
      # Slow amber pulse: effect 45 = pulse in WLED, speed 64 = slow
      local payload='{"on":true,"bri":180,"seg":[{"fx":45,"sx":64,"col":["FF8C00","000000","000000"]}]}'
      _wled_send "$WLED_WORKSTATION" "$payload"
      _log "INFO" "signal_workstation: notable — slow amber pulse"
      echo -e "  ${EMBER_DIM}Workstation LEDs:${RESET}  ${TEXT}amber pulse (notable)${RESET}"
      ;;
    critical)
      # Fast red pulse: speed 220 = fast
      local payload='{"on":true,"bri":255,"seg":[{"fx":45,"sx":220,"col":["FF2200","000000","000000"]}]}'
      _wled_send "$WLED_WORKSTATION" "$payload"
      _log "INFO" "signal_workstation: critical — fast red pulse"
      echo -e "  ${RED}Workstation LEDs:${RESET}  ${TEXT}red pulse (critical)${RESET}"
      ;;
    clear)
      # Return to ember: soft gentle pulse at idle brightness
      local payload='{"on":true,"bri":120,"seg":[{"fx":45,"sx":30,"col":["FF5900","000000","000000"]}]}'
      _wled_send "$WLED_WORKSTATION" "$payload"
      _log "INFO" "signal_workstation: cleared — returned to ember"
      echo -e "  ${EMBER}Workstation LEDs:${RESET}  ${TEXT}ember (cleared)${RESET}"
      ;;
    *)
      _log "WARN" "signal_workstation: unknown severity '${severity}'"
      ;;
  esac
}

# ── signal_bedroom <severity> ─────────────────────────────────────────────────
# Drives the bedroom panel — more aggressive because Nathan has left the desk.
#   notable  → solid amber (gentle wake-up)
#   critical → strobing red (get up NOW)
#   clear    → off (bedroom panel goes dark when not signaling)
signal_bedroom() {
  local severity="${1:-clear}"

  case "$severity" in
    notable)
      # Solid amber, moderate brightness — "hey, something's up"
      local payload='{"on":true,"bri":160,"seg":[{"fx":0,"col":["FF8C00","000000","000000"]}]}'
      _wled_send "$WLED_BEDROOM" "$payload"
      _log "INFO" "signal_bedroom: notable — solid amber"
      echo -e "  ${EMBER_DIM}Bedroom panel:${RESET}  ${TEXT}solid amber (notable)${RESET}"
      ;;
    critical)
      # Strobe effect: WLED effect 10 = strobe — high intensity, get UP
      local payload='{"on":true,"bri":255,"seg":[{"fx":10,"sx":180,"col":["FF2200","000000","000000"]}]}'
      _wled_send "$WLED_BEDROOM" "$payload"
      _log "WARN" "signal_bedroom: critical — strobing red"
      echo -e "  ${RED}Bedroom panel:${RESET}  ${TEXT}strobe red (critical — escalated)${RESET}"
      ;;
    clear)
      # Off — bedroom panel only lights up when signaling
      local payload='{"on":false}'
      _wled_send "$WLED_BEDROOM" "$payload"
      _log "INFO" "signal_bedroom: cleared — panel off"
      ;;
    *)
      _log "WARN" "signal_bedroom: unknown severity '${severity}'"
      ;;
  esac
}

# ── signal_openrgb <severity> ─────────────────────────────────────────────────
# Sends profile load requests to OpenRGB REST API for keyboard/Corsair hardware.
# OpenRGB profiles ("alert", "ember") are configured separately in the OpenRGB GUI.
# This function is gracefully silent if OpenRGB isn't running.
signal_openrgb() {
  local severity="${1:-clear}"
  local openrgb_base="http://${OPENRGB_HOST}:${OPENRGB_PORT}"

  case "$severity" in
    critical)
      local profile="alert"
      ;;
    notable)
      local profile="alert"
      ;;
    clear)
      local profile="ember"
      ;;
    *)
      local profile="ember"
      ;;
  esac

  # Check if OpenRGB is reachable before attempting anything
  if ! curl -sf "${openrgb_base}/api/profiles" --max-time 2 > /dev/null 2>&1; then
    _log "DEBUG" "signal_openrgb: OpenRGB not reachable at ${openrgb_base} — skipping"
    return 0
  fi

  # Load the profile via POST
  # TODO: OpenRGB profiles "alert" and "ember" need to be created and saved
  #       in the OpenRGB GUI before these will do anything meaningful.
  if curl -sf -X POST \
       -H "Content-Type: application/json" \
       -d "{\"name\":\"${profile}\"}" \
       "${openrgb_base}/api/profiles" \
       --max-time 3 \
       > /dev/null 2>&1; then
    _log "INFO" "signal_openrgb: loaded profile '${profile}' (severity: ${severity})"
  else
    _log "WARN" "signal_openrgb: failed to load profile '${profile}'"
  fi
}

# ── _escalation_timer <severity> ─────────────────────────────────────────────
# Background process: waits 10 minutes, then fires bedroom panel if no ack.
# Runs as a subshell so it doesn't block the caller.
_escalation_timer() {
  local severity="$1"
  local wait_seconds=600  # 10 minutes

  sleep "$wait_seconds"

  # If ack file exists, Dad already saw it — stand down
  if [ -f "$TC_ACK_FILE" ]; then
    _log "INFO" "escalation_timer: ack found after ${wait_seconds}s — bedroom escalation cancelled"
    return 0
  fi

  # No ack — fire bedroom panel
  _log "WARN" "escalation_timer: no ack after ${wait_seconds}s — escalating to bedroom panel"
  signal_bedroom "$severity"
}

# ── escalate_to_dad <message> <severity> ─────────────────────────────────────
# The main function other scripts call when TC needs Nathan's attention.
# Writes signal state, fires workstation LEDs, starts background escalation timer.
#
# Usage: escalate_to_dad "Forge is down" "critical"
#        escalate_to_dad "New inbox message from Vesper" "notable"
escalate_to_dad() {
  local message="${1:-TC needs your attention}"
  local severity="${2:-notable}"
  local ts
  ts=$(date -Iseconds)

  # Write signal state file (read by charos ack and other scripts)
  mkdir -p "$(dirname "$TC_SIGNAL_STATE")" 2>/dev/null || true
  {
    echo "timestamp: ${ts}"
    echo "severity: ${severity}"
    echo "message: ${message}"
  } > "$TC_SIGNAL_STATE"

  # Log it
  _log "INFO" "escalate_to_dad: severity=${severity} message='${message}'"

  # Fire all the lights
  signal_workstation "$severity"
  signal_openrgb "$severity"

  # Start background escalation timer — 10 min → bedroom panel if no ack
  ( _escalation_timer "$severity" ) &
  disown $!
  _log "INFO" "escalate_to_dad: escalation timer started (PID $!), bedroom fires in 10min if no ack"

  # Terminal feedback
  echo ""
  echo -e "  ${EMBER}${BOLD}TC Signal${RESET}  ${MUTED}→${RESET}  ${TEXT}${message}${RESET}"
  echo -e "  ${MUTED}Severity:${RESET}  ${TEXT}${severity}${RESET}"
  echo -e "  ${MUTED}Bedroom escalation in 10 min if no ack.${RESET}"
  echo -e "  ${MUTED}Run ${TEXT}charos ack${MUTED} to clear.${RESET}"
  echo ""
}

# ── clear_signal ──────────────────────────────────────────────────────────────
# Called by `charos ack`. Removes state files and returns all lights to idle.
clear_signal() {
  local ts
  ts=$(date -Iseconds)

  # Read what we're clearing (for the log)
  local prev_msg=""
  local prev_sev=""
  if [ -f "$TC_SIGNAL_STATE" ]; then
    prev_sev=$(grep '^severity:' "$TC_SIGNAL_STATE" | cut -d' ' -f2-)
    prev_msg=$(grep '^message:' "$TC_SIGNAL_STATE" | cut -d' ' -f2-)
  fi

  # Remove state files
  rm -f "$TC_ACK_FILE" "$TC_SIGNAL_STATE"

  # Return lights to idle
  signal_workstation clear
  signal_bedroom clear
  signal_openrgb clear

  _log "INFO" "clear_signal: acknowledged at ${ts} — was severity='${prev_sev}' message='${prev_msg}'"

  echo ""
  echo -e "  ${GREEN}Signal cleared.${RESET}  ${MUTED}Lights returning to idle.${RESET}"
  [ -n "$prev_msg" ] && echo -e "  ${MUTED}Was:${RESET}  ${TEXT}[${prev_sev}]${RESET}  ${MUTED}${prev_msg}${RESET}"
  echo ""
}

# ── Direct invocation ─────────────────────────────────────────────────────────
# Allows calling: tc-signal.sh escalate "message" "severity"
#                 tc-signal.sh clear
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  SUBCMD="${1:-}"
  shift || true
  case "$SUBCMD" in
    escalate)   escalate_to_dad "$@" ;;
    clear)      clear_signal ;;
    workstation) signal_workstation "$@" ;;
    bedroom)    signal_bedroom "$@" ;;
    openrgb)    signal_openrgb "$@" ;;
    *)
      echo -e "  ${MUTED}Usage:${RESET}  ${TEXT}tc-signal.sh <escalate|clear|workstation|bedroom|openrgb> [args]${RESET}"
      exit 1
      ;;
  esac
fi
