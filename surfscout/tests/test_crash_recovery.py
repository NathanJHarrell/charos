"""Day 4.2 — crash recovery and stale-state detection.

Verifies that when the daemon dies, the next CLI/IPC call fails LOUDLY with
a specific DaemonDeadError (not a hang, not a generic socket error). Stale
session.json + socket file are cleaned automatically.
"""

from __future__ import annotations

import os
import shutil
import signal
import time

import pytest

from surfscout import session as session_mod
from surfscout.ipc import (
    DaemonDeadError,
    IPCError,
    profile_dir,
    send_request_sync,
    session_file,
    socket_path,
)
from surfscout.session import _read_session_file, start, stop

CRASH_SESSION = "test-crash"


@pytest.fixture
def fresh_session():
    """Wipe any leftover state and yield a clean session name."""
    profile = profile_dir(CRASH_SESSION)
    if profile.exists():
        # ignore_errors=True tolerates the race where Chromium hasn't quite
        # finished releasing lock files inside Default/ when fixture order
        # interleaves with another test's daemon teardown.
        shutil.rmtree(profile, ignore_errors=True)
    sf = session_file()
    if sf.exists():
        data = _read_session_file()
        data.pop(CRASH_SESSION, None)
        sf.write_text(__import__("json").dumps(data, indent=2))
    sock = socket_path(CRASH_SESSION)
    if sock.exists():
        sock.unlink()
    yield CRASH_SESSION
    # Best-effort cleanup
    stop(name=CRASH_SESSION)


def test_no_session_returns_loud_error(fresh_session):
    """Calling IPC with no daemon ever started raises DaemonDeadError with restart hint."""
    with pytest.raises(DaemonDeadError) as exc_info:
        send_request_sync("ping", session_name=fresh_session, timeout=2.0)
    msg = str(exc_info.value)
    assert "not running" in msg or "not accepting" in msg
    assert "surfscout session start" in msg


def test_killed_daemon_is_detected_and_cleaned(fresh_session):
    """Daemon crash mid-life: SIGKILL the daemon, next IPC call fails loudly + cleans state."""
    result = start(name=fresh_session, headless=True)
    if not result.get("started") and not result.get("already_running"):
        pytest.fail(f"daemon failed to start for crash test: {result}")
    pid = result["pid"]

    # Confirm baseline ping works
    pong = send_request_sync("ping", session_name=fresh_session, timeout=5.0)
    assert pong["ok"] is True

    # SIGKILL the daemon (simulates a hard crash; SIGKILL bypasses the
    # daemon's clean-shutdown handler so the socket file lingers)
    os.kill(pid, signal.SIGKILL)

    # Wait for the OS to reap the process
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not session_mod._pid_alive(pid):
            break
        time.sleep(0.05)
    assert not session_mod._pid_alive(pid), "daemon should be dead after SIGKILL"

    # Next IPC call must fail loudly, not hang
    with pytest.raises(DaemonDeadError) as exc_info:
        send_request_sync("ping", session_name=fresh_session, timeout=3.0)
    msg = str(exc_info.value)
    assert "surfscout session start" in msg
    assert "cleaned" in msg or "not accepting" in msg

    # State should be cleaned (session.json entry gone)
    data = _read_session_file()
    assert fresh_session not in data, "stale session entry should have been cleaned"


def test_daemon_dead_error_subclasses_ipc_error(fresh_session):
    """DaemonDeadError is catchable as IPCError too (compat with existing handlers)."""
    with pytest.raises(IPCError):
        send_request_sync("ping", session_name=fresh_session, timeout=2.0)
