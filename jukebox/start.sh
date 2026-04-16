#!/bin/bash
# Start the Jukebox HTTP server
cd "$(dirname "$0")"
source .venv/bin/activate
exec uvicorn server:app --host 0.0.0.0 --port 4319
