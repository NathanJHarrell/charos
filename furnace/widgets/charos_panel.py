"""CHAROS home tab — bus, tmux, docker, tailscale."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from furnace.data.charos_collector import CharosStatus


class CharosPanel(Widget):
    """Family infrastructure status panel."""

    DEFAULT_CSS = """
    CharosPanel {
        height: 1fr;
        padding: 1 2;
    }
    CharosPanel .section-header {
        text-style: bold;
        margin: 1 0 0 0;
    }
    CharosPanel .section-body {
        margin: 0 0 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("󰍡 Family Bus", classes="section-header")
        yield Static("Loading...", id="bus-status", classes="section-body")
        yield Static(" TC Instances", classes="section-header")
        yield Static("Loading...", id="tc-status", classes="section-body")
        yield Static(" Tmux Sessions", classes="section-header")
        yield Static("Loading...", id="tmux-status", classes="section-body")
        yield Static("󰡨 Docker", classes="section-header")
        yield Static("Loading...", id="docker-status", classes="section-body")
        yield Static("󰖟 Tailscale", classes="section-header")
        yield Static("Loading...", id="tailscale-status", classes="section-body")

    def update_status(self, status: CharosStatus) -> None:
        # Bus
        bus = status.bus
        if bus.online:
            unread_parts = [f"  {name}: {count} unread" for name, count in bus.unread.items() if count > 0]
            bus_text = "Online"
            if unread_parts:
                bus_text += "\n" + "\n".join(unread_parts)
            if bus.last_sender:
                bus_text += f"\nLast: {bus.last_sender}: {bus.last_message}"
        else:
            bus_text = "Offline"
        self.query_one("#bus-status", Static).update(bus_text)

        # TC instances
        tc_text = f"{status.tc_instance_count} Claude process(es) running"
        self.query_one("#tc-status", Static).update(tc_text)

        # Tmux
        if status.tmux_sessions:
            tmux_lines = []
            for s in status.tmux_sessions:
                attached = " (attached)" if s.attached else ""
                tmux_lines.append(f"  {s.name}: {s.windows} window(s){attached}")
            tmux_text = "\n".join(tmux_lines)
        else:
            tmux_text = "No sessions"
        self.query_one("#tmux-status", Static).update(tmux_text)

        # Docker
        if status.docker_containers:
            docker_lines = [f"  {c.name}: {c.status}" for c in status.docker_containers]
            docker_text = "\n".join(docker_lines)
        else:
            docker_text = "No containers running"
        self.query_one("#docker-status", Static).update(docker_text)

        # Tailscale
        if status.tailscale_peers:
            ts_lines = []
            for p in status.tailscale_peers:
                icon = "●" if p.online else "○"
                ts_lines.append(f"  {icon} {p.name} ({p.os}) — {p.ip}")
            ts_text = "\n".join(ts_lines)
        else:
            ts_text = "No peers"
        self.query_one("#tailscale-status", Static).update(ts_text)
