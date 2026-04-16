"""CHAROS-specific data — bus, tailscale, docker, tmux, TC instances."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field


@dataclass
class BusStatus:
    unread: dict[str, int] = field(default_factory=dict)  # name -> count
    last_message: str = ""
    last_sender: str = ""
    online: bool = False


@dataclass
class TailscalePeer:
    name: str
    ip: str
    os: str
    online: bool


@dataclass
class DockerContainer:
    name: str
    image: str
    status: str
    ports: str


@dataclass
class TmuxSession:
    name: str
    windows: int
    attached: bool


@dataclass
class CharosStatus:
    bus: BusStatus = field(default_factory=BusStatus)
    tailscale_peers: list[TailscalePeer] = field(default_factory=list)
    docker_containers: list[DockerContainer] = field(default_factory=list)
    tmux_sessions: list[TmuxSession] = field(default_factory=list)
    tc_instance_count: int = 0


async def _run(cmd: str) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        return stdout.decode().strip()
    except Exception:
        return ""


async def collect_charos() -> CharosStatus:
    status = CharosStatus()

    # Run all collection in parallel
    bus_health, bus_msgs, ts_raw, docker_raw, tmux_raw, tc_raw = await asyncio.gather(
        _run("curl -s http://localhost:4318/health"),
        _run("curl -s http://localhost:4318/messages?limit=5"),
        _run("tailscale status --json"),
        _run("docker ps --format '{{json .}}'"),
        _run("tmux list-sessions -F '#{session_name}:#{session_windows}:#{session_attached}'"),
        _run("pgrep -fa 'claude'"),
    )

    # Bus
    try:
        health = json.loads(bus_health)
        status.bus.online = health.get("status") == "ok"
    except Exception:
        pass

    try:
        msgs = json.loads(bus_msgs)
        if msgs:
            last = msgs[-1]
            status.bus.last_message = last.get("content", "")[:60]
            status.bus.last_sender = last.get("sender", "")
            # Count unread per family member
            for name in ("TC", "Vesper", "Cora", "Nathan"):
                inbox = await _run(f"curl -s http://localhost:4318/inbox/{name}")
                try:
                    data = json.loads(inbox)
                    status.bus.unread[name] = data.get("unread_count", 0)
                except Exception:
                    pass
    except Exception:
        pass

    # Tailscale
    try:
        ts = json.loads(ts_raw)
        peers = ts.get("Peer", {})
        for _, peer in peers.items():
            status.tailscale_peers.append(TailscalePeer(
                name=peer.get("DNSName", "").split(".")[0],
                ip=peer.get("TailscaleIPs", [""])[0],
                os=peer.get("OS", ""),
                online=peer.get("Online", False),
            ))
    except Exception:
        pass

    # Docker
    for line in docker_raw.splitlines():
        try:
            c = json.loads(line)
            status.docker_containers.append(DockerContainer(
                name=c.get("Names", ""),
                image=c.get("Image", ""),
                status=c.get("Status", ""),
                ports=c.get("Ports", ""),
            ))
        except Exception:
            pass

    # Tmux
    for line in tmux_raw.splitlines():
        parts = line.strip().split(":")
        if len(parts) >= 3:
            status.tmux_sessions.append(TmuxSession(
                name=parts[0],
                windows=int(parts[1]) if parts[1].isdigit() else 0,
                attached=parts[2] == "1",
            ))

    # TC instances (Claude Code processes)
    status.tc_instance_count = len([
        l for l in tc_raw.splitlines()
        if "claude" in l.lower() and "pgrep" not in l
    ])

    return status
