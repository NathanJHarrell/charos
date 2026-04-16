"""
clipd — Jarvis Daemon
Watches Windows clipboard via PowerShell, syncs with Nest over TCP.
Connects to nest:4201. Protocol: newline-delimited JSON, base64 content.
"""

import asyncio
import base64
import hashlib
import json
import os
import socket
import subprocess
import time

SERVER = os.environ.get("CLIPD_SERVER", "nest")
PORT = int(os.environ.get("CLIPD_PORT", "4201"))
POLL_INTERVAL = 0.5
MAX_CONTENT = 1_048_576  # 1MB
HOSTNAME = socket.gethostname()
RECONNECT_BASE = 1
RECONNECT_MAX = 30

last_hash = ""
suppress_next = False
writer_ref: asyncio.StreamWriter | None = None


def get_clipboard() -> str:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.rstrip("\r\n")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def set_clipboard(content: str):
    global suppress_next
    try:
        # Pipe via stdin to avoid shell escaping issues
        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command",
             "$input | Set-Clipboard"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.communicate(input=content.encode("utf-8"), timeout=3)
        suppress_next = True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[clipd] Set-Clipboard failed: {e}")


def content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


def make_message(content: str) -> bytes:
    msg = {
        "type": "clip",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "source": HOSTNAME,
        "ts": time.time(),
    }
    return (json.dumps(msg) + "\n").encode("utf-8")


async def clipboard_watcher():
    global last_hash, suppress_next, writer_ref

    content = get_clipboard()
    last_hash = content_hash(content) if content else ""

    while True:
        await asyncio.sleep(POLL_INTERVAL)

        if suppress_next:
            suppress_next = False
            content = get_clipboard()
            last_hash = content_hash(content) if content else last_hash
            continue

        content = get_clipboard()
        if not content or len(content) > MAX_CONTENT:
            continue

        h = content_hash(content)
        if h == last_hash:
            continue

        last_hash = h
        print(f"[clipd] local clipboard changed ({len(content)} bytes)")

        if writer_ref:
            try:
                writer_ref.write(make_message(content))
                await writer_ref.drain()
            except Exception:
                pass


async def handle_incoming(reader: asyncio.StreamReader):
    global last_hash

    while True:
        line = await reader.readline()
        if not line:
            break

        try:
            msg = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if msg.get("type") != "clip":
            continue
        if msg.get("source") == HOSTNAME:
            continue

        raw = base64.b64decode(msg["content"]).decode("utf-8", errors="replace")
        if len(raw) > MAX_CONTENT:
            continue

        h = content_hash(raw)
        if h == last_hash:
            continue

        last_hash = h
        print(f"[clipd] received from {msg.get('source', '?')} ({len(raw)} bytes)")
        set_clipboard(raw)


async def connect_loop():
    global writer_ref
    backoff = RECONNECT_BASE

    while True:
        try:
            print(f"[clipd] connecting to {SERVER}:{PORT}...")
            reader, writer = await asyncio.open_connection(SERVER, PORT)
            writer_ref = writer
            backoff = RECONNECT_BASE
            print(f"[clipd] connected to {SERVER}:{PORT}")

            await handle_incoming(reader)

        except (ConnectionRefusedError, OSError, asyncio.IncompleteReadError) as e:
            print(f"[clipd] connection lost: {e}")
        finally:
            writer_ref = None

        print(f"[clipd] reconnecting in {backoff}s...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, RECONNECT_MAX)


async def main():
    print(f"[clipd] jarvis daemon starting (server: {SERVER}:{PORT})")
    await asyncio.gather(
        connect_loop(),
        clipboard_watcher(),
    )


if __name__ == "__main__":
    asyncio.run(main())
