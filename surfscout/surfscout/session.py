"""Session management — start/stop/status for the SurfScout daemon.

start: detects existing session; if none, double-forks a daemon and writes
       session.json; waits for the socket to be ready and pings the daemon.
stop:  reads session.json, sends SIGTERM to the daemon PID, cleans state.
status: reads session.json, pings the daemon, prints state.

session.json schema (dict-keyed by session name from day one):
{
  "default": {
    "pid": 12345,
    "socket": "/home/nate/.surfscout/sock-default",
    "started_at": 1714512000.0,
    "headless": false
  },
  "<other-name>": { ... }
}
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from surfscout.ipc import (
    DEFAULT_SESSION_NAME,
    IPCError,
    ensure_state_dir,
    send_request_sync,
    session_file,
    socket_path,
)

START_TIMEOUT_SEC = 15.0  # how long to wait for daemon socket to become ready
START_PING_INTERVAL = 0.1


def _read_session_file() -> dict[str, dict[str, Any]]:
    """Return the parsed session.json, or empty dict if missing/corrupt."""
    path = session_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_session_file(data: dict[str, dict[str, Any]]) -> None:
    """Write session.json atomically."""
    ensure_state_dir()
    path = session_file()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _pid_alive(pid: int) -> bool:
    """Check whether a PID is alive AND not a zombie (Linux-aware).

    A zombie (defunct) process technically still exists in the process table
    (so `kill -0` succeeds) but cannot accept connections, respond to IPC, or
    do any actual work. For SurfScout's purposes, a zombie daemon IS dead.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but we don't own it; assume alive

    # Zombie check — Linux exposes process state via /proc/<pid>/status
    status_path = Path(f"/proc/{pid}/status")
    if status_path.exists():
        try:
            for line in status_path.read_text().splitlines():
                if line.startswith("State:"):
                    # State line is e.g. "State:	Z (zombie)" or "State:	S (sleeping)"
                    state_char = line.split()[1] if len(line.split()) > 1 else ""
                    if state_char == "Z":
                        return False
                    break
        except OSError:
            pass  # /proc reads can race; fall through to "alive"

    return True


def _clean_stale(name: str) -> None:
    """Remove stale session entry + socket file for `name`."""
    data = _read_session_file()
    data.pop(name, None)
    _write_session_file(data)
    sock = socket_path(name)
    if sock.exists():
        sock.unlink()


def status(name: str = DEFAULT_SESSION_NAME) -> dict[str, Any]:
    """Return status for a named session.

    Returns dict with keys: name, running, pid, socket, started_at, ping_ok, error.
    """
    data = _read_session_file()
    entry = data.get(name)
    if not entry:
        return {"name": name, "running": False, "reason": "no session.json entry"}

    pid = entry.get("pid")
    if not pid or not _pid_alive(pid):
        return {
            "name": name,
            "running": False,
            "reason": f"PID {pid} not alive",
            "pid": pid,
            "stale_entry": True,
        }

    sock = socket_path(name)
    if not sock.exists():
        return {
            "name": name,
            "running": False,
            "reason": f"socket {sock} missing",
            "pid": pid,
            "stale_entry": True,
        }

    # Try a real ping
    try:
        ping_result = send_request_sync("ping", session_name=name, timeout=2.0)
        return {
            "name": name,
            "running": True,
            "pid": pid,
            "socket": str(sock),
            "started_at": entry.get("started_at"),
            "headless": entry.get("headless", False),
            "ping": ping_result,
        }
    except IPCError as e:
        return {
            "name": name,
            "running": False,
            "reason": f"ping failed: {e}",
            "pid": pid,
            "stale_entry": True,
        }


def start(name: str = DEFAULT_SESSION_NAME, headless: bool = False) -> dict[str, Any]:
    """Start the daemon for a named session.

    If a session is already running, return its status.
    Otherwise spawn the daemon, wait for socket ready, write session.json.
    """
    ensure_state_dir()

    # If we already have a live session, just return its status
    existing = status(name)
    if existing.get("running"):
        return {"already_running": True, **existing}

    # Clean any stale state before spawning
    if existing.get("stale_entry"):
        _clean_stale(name)

    # Spawn the daemon in a fully-detached subprocess.
    # `start_new_session=True` is the simple equivalent of double-fork: it
    # detaches the child from the controlling terminal so it survives the
    # parent's exit.
    venv_python = Path.home() / "charos" / "surfscout" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        # Fall back to the same interpreter the CLI was invoked with
        venv_python = Path(sys.executable)

    cmd = [str(venv_python), "-m", "surfscout.daemon", "--name", name]
    if headless:
        cmd.append("--headless")

    log_path = Path.home() / ".surfscout" / f"daemon-{name}.log"
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    # Wait for the socket to be ready and the daemon to respond to a ping
    sock = socket_path(name)
    deadline = time.time() + START_TIMEOUT_SEC
    last_error: str | None = None
    while time.time() < deadline:
        if sock.exists():
            try:
                ping_result = send_request_sync("ping", session_name=name, timeout=1.0)
                # Success — write session.json
                entry = {
                    "pid": proc.pid,
                    "socket": str(sock),
                    "started_at": time.time(),
                    "headless": headless,
                }
                data = _read_session_file()
                data[name] = entry
                _write_session_file(data)
                return {
                    "started": True,
                    "name": name,
                    "pid": proc.pid,
                    "socket": str(sock),
                    "ping": ping_result,
                    "log": str(log_path),
                }
            except IPCError as e:
                last_error = str(e)
        # Check whether the daemon process died
        if proc.poll() is not None:
            log.close()
            tail = ""
            try:
                with open(log_path) as f:
                    lines = f.readlines()
                    tail = "".join(lines[-20:])
            except OSError:
                pass
            return {
                "started": False,
                "error": (
                    f"daemon process exited with code {proc.returncode} "
                    f"before becoming ready. Log tail:\n{tail}"
                ),
                "log": str(log_path),
            }
        time.sleep(START_PING_INTERVAL)

    # Timed out — try to kill the orphan
    try:
        proc.terminate()
    except Exception:
        pass
    return {
        "started": False,
        "error": f"daemon did not become ready within {START_TIMEOUT_SEC}s. "
        f"Last ping error: {last_error}",
        "log": str(log_path),
    }


def stop(name: str = DEFAULT_SESSION_NAME) -> dict[str, Any]:
    """Stop the daemon for a named session.

    Sends SIGTERM, waits up to 5s for clean exit, then cleans state.
    """
    data = _read_session_file()
    entry = data.get(name)
    if not entry:
        return {"stopped": False, "reason": "no session.json entry"}

    pid = entry.get("pid")
    if not pid:
        _clean_stale(name)
        return {"stopped": False, "reason": "no PID in session entry; cleaned"}

    if not _pid_alive(pid):
        _clean_stale(name)
        return {"stopped": True, "reason": f"PID {pid} was not alive; cleaned state"}

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _clean_stale(name)
        return {"stopped": True, "reason": "process disappeared during stop; cleaned"}

    # Wait for clean exit
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if not _pid_alive(pid):
            _clean_stale(name)
            return {"stopped": True, "pid": pid}
        time.sleep(0.1)

    # Hard kill if still alive
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    _clean_stale(name)
    return {"stopped": True, "pid": pid, "method": "SIGKILL"}
