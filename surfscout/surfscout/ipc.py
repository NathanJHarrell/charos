"""IPC protocol + Unix domain socket client for SurfScout.

The daemon at ~/.surfscout/sock-<name> speaks newline-delimited JSON.
Each request is a single line: {"method": "<name>", "args": {...}}
Each response is a single line: {"ok": true|false, "result": {...}|null, "error": "..."}

Mirrors the clipd/nest_daemon.py pattern, adapted for UDS + method dispatch.
"""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import Any

# State directory layout
STATE_DIR = Path.home() / ".surfscout"
DEFAULT_SESSION_NAME = "default"


def socket_path(session_name: str = DEFAULT_SESSION_NAME) -> Path:
    """Return the UDS path for a named session."""
    return STATE_DIR / f"sock-{session_name}"


def session_file(session_name: str = DEFAULT_SESSION_NAME) -> Path:
    """Return the session metadata JSON path for a named session.

    Note: a single session.json holds metadata for all named sessions
    (dict keyed by name). This function returns the same path regardless
    of session_name; the name is the key inside the file.
    """
    return STATE_DIR / "session.json"


def profile_dir(session_name: str = DEFAULT_SESSION_NAME) -> Path:
    """Return the persistent Playwright user-data dir for a named session."""
    return STATE_DIR / f"profile-{session_name}"


def ensure_state_dir() -> None:
    """Create ~/.surfscout/ if it doesn't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


class IPCError(Exception):
    """Raised when the daemon returns an error or is unreachable."""


class DaemonDeadError(IPCError):
    """Raised when the daemon process is verifiably dead.

    Distinguished from generic IPCError so callers (and the CLI) can render
    a specific "your session is gone, restart" message instead of a generic
    connection-failed dump. The error message always includes the restart
    hint and confirms whether stale state was cleaned.
    """


def _detect_and_clean_stale(session_name: str) -> str | None:
    """Detect dead daemon, clean stale state, return human-readable status.

    Returns a string describing what was cleaned, or None if state looked OK.
    """
    # Lazy import to avoid circular dependency (session.py imports from ipc)
    from surfscout import session as _session

    data = _session._read_session_file()
    entry = data.get(session_name)
    if not entry:
        return None

    pid = entry.get("pid")
    pid_alive = pid and _session._pid_alive(pid)
    sock_exists = socket_path(session_name).exists()

    if not pid_alive:
        _session._clean_stale(session_name)
        return f"daemon PID {pid} is dead; cleaned stale session.json + socket"
    if not sock_exists:
        _session._clean_stale(session_name)
        return f"daemon PID {pid} is alive but socket missing; cleaned stale state (daemon may be a zombie — kill it manually if needed)"
    return None


def send_request_sync(
    method: str,
    args: dict[str, Any] | None = None,
    session_name: str = DEFAULT_SESSION_NAME,
    timeout: float = 30.0,
) -> Any:
    """Send a request to the daemon synchronously, return result on success.

    Raises IPCError on daemon-side error.
    Raises DaemonDeadError on dead/missing daemon (auto-cleans stale state).
    """
    sock_path = socket_path(session_name)
    if not sock_path.exists():
        cleaned = _detect_and_clean_stale(session_name)
        msg = f"surfscout session '{session_name}' is not running (no socket at {sock_path})."
        if cleaned:
            msg += f" {cleaned}."
        msg += " Run `surfscout session start` to start a new one."
        raise DaemonDeadError(msg)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        try:
            sock.connect(str(sock_path))
        except (ConnectionRefusedError, FileNotFoundError) as e:
            cleaned = _detect_and_clean_stale(session_name)
            msg = (
                f"surfscout daemon at {sock_path} is not accepting connections "
                f"({type(e).__name__}: {e})."
            )
            if cleaned:
                msg += f" {cleaned}."
            msg += " Run `surfscout session start` to start a new one."
            raise DaemonDeadError(msg) from e

        try:
            request = json.dumps({"method": method, "args": args or {}}) + "\n"
            sock.sendall(request.encode("utf-8"))

            # Read until newline
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    cleaned = _detect_and_clean_stale(session_name)
                    msg = "daemon closed connection without response (likely crashed mid-request)."
                    if cleaned:
                        msg += f" {cleaned}."
                    msg += " Run `surfscout session start` to start a new one."
                    raise DaemonDeadError(msg)
                buf += chunk

            response = json.loads(buf.decode("utf-8").rstrip("\n"))
        except socket.timeout as e:
            raise IPCError(
                f"daemon did not respond within {timeout}s. "
                f"It may be stuck on a slow page; consider `surfscout session stop` "
                f"and restart if this persists."
            ) from e
    finally:
        sock.close()

    if not response.get("ok"):
        raise IPCError(response.get("error", "unknown daemon error"))
    return response.get("result")


async def send_request_async(
    method: str,
    args: dict[str, Any] | None = None,
    session_name: str = DEFAULT_SESSION_NAME,
    timeout: float = 30.0,
) -> Any:
    """Async version of send_request_sync. Used internally by the daemon for self-test."""
    sock_path = socket_path(session_name)
    if not sock_path.exists():
        raise IPCError(f"surfscout daemon socket not found at {sock_path}")

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(sock_path)), timeout=timeout
        )
    except (ConnectionRefusedError, FileNotFoundError, asyncio.TimeoutError) as e:
        raise IPCError(f"Could not connect to surfscout daemon: {e}") from e

    try:
        request = json.dumps({"method": method, "args": args or {}}) + "\n"
        writer.write(request.encode("utf-8"))
        await writer.drain()

        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            raise IPCError("daemon closed connection without response")
        response = json.loads(line.decode("utf-8").rstrip("\n"))
    finally:
        writer.close()
        await writer.wait_closed()

    if not response.get("ok"):
        raise IPCError(response.get("error", "unknown daemon error"))
    return response.get("result")
