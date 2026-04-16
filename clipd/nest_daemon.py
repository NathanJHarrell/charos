"""
clipd — Nest Daemon
Watches Wayland clipboard, syncs with Jarvis over TCP.
Port 4201. Protocol: newline-delimited JSON, base64 content.
"""

import asyncio
import base64
import hashlib
import json
import socket
import subprocess
import time

HOST = "0.0.0.0"
PORT = 4201
POLL_INTERVAL = 0.5
MAX_CONTENT = 1_048_576  # 1MB
HOSTNAME = socket.gethostname()

clients: set[asyncio.StreamWriter] = set()
last_hash = ""
suppress_next = False  # prevent echo loops


def get_clipboard() -> str:
    try:
        result = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True, timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def set_clipboard(content: str):
    global suppress_next
    try:
        proc = subprocess.Popen(
            ["wl-copy"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=content.encode("utf-8"), timeout=2)
        suppress_next = True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[clipd] wl-copy failed: {e}")


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


async def broadcast(data: bytes, exclude: asyncio.StreamWriter | None = None):
    dead = set()
    for writer in clients:
        if writer is exclude:
            continue
        try:
            writer.write(data)
            await writer.drain()
        except Exception:
            dead.add(writer)
    for w in dead:
        clients.discard(w)
        try:
            w.close()
        except Exception:
            pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global last_hash
    addr = writer.get_extra_info("peername")
    print(f"[clipd] client connected: {addr}")
    clients.add(writer)

    try:
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

            # Relay to other clients
            await broadcast(line, exclude=writer)

    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        print(f"[clipd] client disconnected: {addr}")
        clients.discard(writer)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def clipboard_watcher():
    global last_hash, suppress_next

    # Initialize hash
    content = get_clipboard()
    last_hash = content_hash(content) if content else ""

    while True:
        await asyncio.sleep(POLL_INTERVAL)

        if suppress_next:
            # We just set the clipboard ourselves, skip one poll
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
        await broadcast(make_message(content))


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[clipd] nest daemon listening on {addr[0]}:{addr[1]}")

    async with server:
        await asyncio.gather(
            server.serve_forever(),
            clipboard_watcher(),
        )


if __name__ == "__main__":
    asyncio.run(main())
