# clipd — Network Clipboard Daemon

Syncs clipboard between Nest (Wayland) and Jarvis (Windows) over TCP.

## Usage

```bash
clipd nest          # Start Nest daemon (server, port 4201)
clipd jarvis        # Start Jarvis daemon (client, connects to nest:4201)
clipd status        # Show running clipd processes
clipd stop          # Kill running clipd
```

## How It Works

- Nest daemon polls `wl-paste` every 500ms, serves on TCP port 4201
- Jarvis daemon polls `powershell.exe Get-Clipboard` every 500ms, connects to Nest
- Changes are sent as newline-delimited JSON with base64-encoded content
- Echo loops prevented via source hostname + content hash deduplication
- Jarvis auto-reconnects with exponential backoff (max 30s)

## Environment

- `CLIPD_SERVER` — Jarvis daemon: hostname to connect to (default: `nest`)
- `CLIPD_PORT` — port override (default: `4201`)

## Protocol

```json
{"type": "clip", "content": "<base64>", "source": "<hostname>", "ts": 1234567890.123}
```
