#!/usr/bin/env bash
# CHAROS — Environment Configuration
# Sourced by zshrc and all CHAROS scripts.
# Single source of truth for paths, ports, and device addresses.

# ── Core paths ────────────────────────────────────────────────────────────────
export CHAROS_HOME=/home/nathan/.charos
export FORGE_DIR=/home/nathan/forge

# ── Service ports ─────────────────────────────────────────────────────────────
export FORGE_PORT=3001

# ── OpenRGB (Corsair keyboard + hardware strips) ───────────────────────────────
export OPENRGB_HOST=localhost
export OPENRGB_PORT=6800

# ── WLED controllers ──────────────────────────────────────────────────────────
# NOTE: Update these IPs when hardware arrives and devices get fixed DHCP leases.
# WLED_WORKSTATION: WS2812B strips in the workstation area (desk, ambient)
export WLED_WORKSTATION=http://192.168.1.200
# WLED_BEDROOM: Panel in Nathan's bedroom — used for escalation when he's away from desk
export WLED_BEDROOM=http://192.168.1.201

# ── TC communication files ────────────────────────────────────────────────────
export TC_INBOX=/tmp/charos-inbox
export TC_ACK_FILE=/tmp/charos-ack
export TC_LOG_DIR=/var/log/charos

# ── Signal state (written by tc-signal.sh, read by charos ack) ────────────────
export TC_SIGNAL_STATE=/tmp/charos-signal-state
