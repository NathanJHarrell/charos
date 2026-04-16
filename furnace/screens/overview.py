"""Overview tab — stat cards + sparkline grid + Charizard watermark."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Grid
from textual.widget import Widget

from furnace.widgets.stat_card import StatCard
from furnace.widgets.sparkline import SparklineChart, _human_bytes
from furnace.widgets.charizard import CharizardWatermark
from furnace.data.collector import SystemSnapshot


class OverviewTab(Widget):

    DEFAULT_CSS = """
    OverviewTab {
        height: 1fr;
    }
    #stat-row {
        height: 3;
        margin: 0 0 1 0;
    }
    #chart-grid {
        height: auto;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 0 1;
    }
    #watermark {
        height: auto;
        min-height: 23;
        content-align: center middle;
        text-align: center;
        color: #8a6a30;
        margin: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="stat-row"):
            yield StatCard(icon="", label="CPU", id="stat-cpu")
            yield StatCard(icon="", label="MEM", id="stat-mem")
            yield StatCard(icon="󰈀", label="NET", id="stat-net")
            yield StatCard(icon="󰋊", label="DISK", id="stat-disk")
        with Grid(id="chart-grid"):
            yield SparklineChart(label="CPU", icon="", max_val=100, unit="%", id="chart-cpu")
            yield SparklineChart(label="Memory", icon="", max_val=100, unit="%", id="chart-mem")
            yield SparklineChart(label="Network", icon="󰈀", max_val=1, unit="B/s", id="chart-net")
            yield SparklineChart(label="Disk I/O", icon="󰋊", max_val=1, unit="B/s", id="chart-disk")
        yield CharizardWatermark(id="watermark")

    def update_data(self, snap: SystemSnapshot) -> None:
        # Stat cards
        self.query_one("#stat-cpu", StatCard).set_value(f"{snap.cpu_percent:.1f}%")
        self.query_one("#stat-mem", StatCard).set_value(
            f"{_human_bytes(snap.mem_used)} / {_human_bytes(snap.mem_total)}"
        )
        net_total = snap.net_recv_rate + snap.net_send_rate
        self.query_one("#stat-net", StatCard).set_value(f"{_human_bytes(net_total)}/s")
        disk_total = snap.disk_read_rate + snap.disk_write_rate
        self.query_one("#stat-disk", StatCard).set_value(f"{_human_bytes(disk_total)}/s")

        # Sparklines
        self.query_one("#chart-cpu", SparklineChart).push_value(snap.cpu_percent)
        self.query_one("#chart-mem", SparklineChart).push_value(snap.mem_percent)
        self.query_one("#chart-net", SparklineChart).push_value(net_total)
        self.query_one("#chart-disk", SparklineChart).push_value(disk_total)
