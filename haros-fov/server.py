"""
HAROS-FOV — Battalion Field of View
FastAPI backend: REST API + WebSocket-to-tmux PTY bridge + static serving.
Port 4200. Discovers haros-* tmux sessions and serves them via xterm.js.
"""

import asyncio
import fcntl
import json
import os
import pty
import re
import signal
import socket
import struct
import termios
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"
STATIC_DIR = Path(__file__).parent / "static"
HOSTNAME = socket.gethostname()
PORT = int(os.environ.get("PORT", 4200))
DISCOVERY_INTERVAL = 5   # seconds between tmux scans
HEALTH_INTERVAL = 30     # seconds between remote health checks

# ── State ───────────────────────────────────────────────────────────────

_builds: dict[str, dict] = {}           # build_name -> {sessions: [...]}
_machines: list[dict] = []              # from config.json
_machine_health: dict[str, bool] = {}   # hostname -> reachable


def _load_config():
    global _machines
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        _machines = cfg.get("machines", [])
    else:
        _machines = [{"hostname": HOSTNAME, "address": "localhost", "local": True}]


# ── tmux Discovery ──────────────────────────────────────────────────────

async def _discover_sessions():
    """Scan tmux for haros-* sessions and group by build name."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "list-sessions", "-F",
            "#{session_name}:#{session_windows}:#{session_attached}:#{session_activity}:#{session_created}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
    except FileNotFoundError:
        return {}

    if proc.returncode != 0:
        return {}

    builds: dict[str, dict] = {}
    now = asyncio.get_event_loop().time()
    import time
    now_epoch = time.time()

    for line in stdout.decode().strip().splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        name, windows, attached, activity, created = parts[0], parts[1], parts[2], parts[3], parts[4]

        if not name.startswith("haros-"):
            continue

        # Parse: haros-{build}-{label}
        remainder = name[6:]  # strip "haros-"
        dash_idx = remainder.find("-")
        if dash_idx == -1:
            build_name = remainder
            label = "default"
        else:
            build_name = remainder[:dash_idx]
            label = remainder[dash_idx + 1:]

        try:
            idle_seconds = int(now_epoch - int(activity))
        except (ValueError, TypeError):
            idle_seconds = 0

        try:
            age_seconds = int(now_epoch - int(created))
        except (ValueError, TypeError):
            age_seconds = 0

        session_info = {
            "name": name,
            "build": build_name,
            "label": label,
            "windows": int(windows),
            "attached": attached == "1",
            "idle_seconds": max(0, idle_seconds),
            "age_seconds": max(0, age_seconds),
        }

        if build_name not in builds:
            builds[build_name] = {
                "name": build_name,
                "machine": HOSTNAME,
                "sessions": [],
                "session_count": 0,
                "age_seconds": age_seconds,
            }

        builds[build_name]["sessions"].append(session_info)
        builds[build_name]["session_count"] = len(builds[build_name]["sessions"])
        # Build age = oldest session
        builds[build_name]["age_seconds"] = max(builds[build_name]["age_seconds"], age_seconds)

    return builds


async def _discovery_loop():
    """Background task: refresh local builds every DISCOVERY_INTERVAL seconds."""
    global _builds
    while True:
        _builds = await _discover_sessions()
        await asyncio.sleep(DISCOVERY_INTERVAL)


async def _health_loop():
    """Background task: check remote agents every HEALTH_INTERVAL seconds."""
    global _machine_health
    while True:
        for machine in _machines:
            if machine.get("local"):
                _machine_health[machine["hostname"]] = True
                continue
            try:
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-m", "3",
                    f"http://{machine['address']}:{PORT}/health",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                _machine_health[machine["hostname"]] = proc.returncode == 0
            except Exception:
                _machine_health[machine["hostname"]] = False
        await asyncio.sleep(HEALTH_INTERVAL)


# ── App ─────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_config()
    t1 = asyncio.create_task(_discovery_loop())
    t2 = asyncio.create_task(_health_loop())
    yield
    t1.cancel()
    t2.cancel()


app = FastAPI(title="HAROS-FOV", lifespan=lifespan)


# ── REST Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "hostname": HOSTNAME,
        "session_count": sum(b["session_count"] for b in _builds.values()),
    }


@app.get("/api/builds")
def list_builds():
    return list(_builds.values())


@app.get("/api/builds/{name}")
def get_build(name: str):
    if name not in _builds:
        return JSONResponse({"error": f"build '{name}' not found"}, status_code=404)
    return _builds[name]


@app.get("/api/builds/{name}/sessions")
def get_build_sessions(name: str):
    if name not in _builds:
        return JSONResponse({"error": f"build '{name}' not found"}, status_code=404)
    return _builds[name]["sessions"]


@app.get("/api/machines")
def list_machines():
    result = []
    for m in _machines:
        result.append({
            "hostname": m["hostname"],
            "address": m["address"],
            "local": m.get("local", False),
            "reachable": _machine_health.get(m["hostname"], False),
        })
    return result


@app.get("/api/machines/{hostname}/builds")
async def get_remote_builds(hostname: str):
    """Proxy: fetch builds from a remote HAROS agent."""
    machine = next((m for m in _machines if m["hostname"] == hostname), None)
    if not machine:
        return JSONResponse({"error": f"unknown machine '{hostname}'"}, status_code=404)

    if machine.get("local"):
        return list(_builds.values())

    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-m", "5",
            f"http://{machine['address']}:{PORT}/api/builds",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return json.loads(stdout.decode())
        return JSONResponse({"error": "remote agent unreachable"}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


# ── WebSocket: Terminal Bridge ──────────────────────────────────────────

@app.websocket("/ws/terminal/{session_name}")
async def terminal_bridge(websocket: WebSocket, session_name: str):
    """Bidirectional PTY bridge between WebSocket and tmux session."""
    await websocket.accept()

    # Validate session exists
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "has-session", "-t", session_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            await websocket.send_json({"type": "error", "data": f"session '{session_name}' not found"})
            await websocket.close()
            return
    except Exception as e:
        await websocket.send_json({"type": "error", "data": str(e)})
        await websocket.close()
        return

    # Create PTY
    master_fd, slave_fd = pty.openpty()

    # Set initial terminal size
    winsize = struct.pack("HHHH", 24, 80, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)

    # Spawn tmux attach with proper terminal type
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    proc = await asyncio.create_subprocess_exec(
        "tmux", "attach-session", "-t", session_name,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        env=env,
    )
    os.close(slave_fd)

    # Make master_fd non-blocking
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    loop = asyncio.get_event_loop()
    closed = asyncio.Event()

    async def read_pty():
        """Read from PTY master and send to WebSocket."""
        try:
            while not closed.is_set():
                await asyncio.sleep(0.01)  # small yield
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    await websocket.send_json({
                        "type": "output",
                        "data": data.decode("utf-8", errors="replace"),
                    })
                except OSError:
                    # EAGAIN — no data available yet
                    continue
        except Exception:
            pass
        finally:
            closed.set()

    async def write_pty():
        """Read from WebSocket and write to PTY master."""
        try:
            while not closed.is_set():
                msg = await websocket.receive_json()
                if msg["type"] == "input":
                    os.write(master_fd, msg["data"].encode("utf-8"))
                elif msg["type"] == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                    # TIOCSWINSZ sends SIGWINCH to tmux — no refresh-client needed
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            closed.set()

    try:
        await asyncio.gather(read_pty(), write_pty())
    finally:
        os.close(master_fd)
        try:
            proc.terminate()
        except ProcessLookupError:
            pass


# ── WebSocket: Cross-Machine Proxy ──────────────────────────────────────

@app.websocket("/ws/proxy/{hostname}/{session_name}")
async def proxy_terminal(websocket: WebSocket, hostname: str, session_name: str):
    """Relay WebSocket to a remote HAROS agent's terminal bridge."""
    await websocket.accept()

    machine = next((m for m in _machines if m["hostname"] == hostname), None)
    if not machine:
        await websocket.send_json({"type": "error", "data": f"unknown machine '{hostname}'"})
        await websocket.close()
        return

    remote_url = f"ws://{machine['address']}:{PORT}/ws/terminal/{session_name}"

    try:
        import websockets as ws_lib
        async with ws_lib.connect(remote_url) as remote_ws:
            closed = asyncio.Event()

            async def browser_to_remote():
                try:
                    while not closed.is_set():
                        data = await websocket.receive_text()
                        await remote_ws.send(data)
                except Exception:
                    closed.set()

            async def remote_to_browser():
                try:
                    async for msg in remote_ws:
                        await websocket.send_text(msg)
                except Exception:
                    closed.set()

            await asyncio.gather(browser_to_remote(), remote_to_browser())
    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"proxy failed: {e}"})
        await websocket.close()


# ── Static Files ────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
