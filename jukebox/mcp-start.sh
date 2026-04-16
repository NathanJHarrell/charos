#!/bin/bash
# Start the Jukebox MCP server (stdio transport for Claude Desktop)
cd "$(dirname "$0")"
source .venv/bin/activate
exec python3 mcp_server.py
