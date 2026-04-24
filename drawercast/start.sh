#!/usr/bin/env bash
# DrawerCast — start the subtitle server on port 1337

cd "$(dirname "$0")"

# Bind to 0.0.0.0 so Jarvis can reach us over Tailscale
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 1337 --reload
