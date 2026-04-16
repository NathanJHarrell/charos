"""Network tab — bandwidth graph + per-interface stats."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, DataTable

from furnace.widgets.sparkline import SparklineChart, _human_bytes
from furnace.data.collector import SystemSnapshot


class NetworkTab(Widget):

    DEFAULT_CSS = """
    NetworkTab {
        height: 1fr;
        padding: 0 1;
    }
    #net-header {
        text-style: bold;
        margin: 0 0 1 0;
    }
    #bw-chart {
        height: 8;
    }
    #nic-table {
        height: 1fr;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("󰈀 Bandwidth", id="net-header")
        yield SparklineChart(
            label="↓ Recv + ↑ Send", icon="󰈀", max_val=1, unit="B/s", id="bw-chart"
        )
        table = DataTable(id="nic-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#nic-table", DataTable)
        table.add_columns("Interface", "↓ Recv/s", "↑ Send/s")

    def update_data(self, snap: SystemSnapshot) -> None:
        total = snap.net_recv_rate + snap.net_send_rate
        self.query_one("#bw-chart", SparklineChart).push_value(total)

        table = self.query_one("#nic-table", DataTable)
        table.clear()
        for nic, (recv, send) in sorted(snap.net_per_nic.items()):
            if nic == "lo":
                continue
            table.add_row(nic, f"{_human_bytes(recv)}/s", f"{_human_bytes(send)}/s")
