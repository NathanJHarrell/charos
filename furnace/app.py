"""Furnace — CHAROS System Monitor TUI.

Charizard's belly. Where the fire comes from. Where the data burns.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual import work

from furnace.data.collector import Collector
from furnace.data.charos_collector import collect_charos
from furnace.screens.overview import OverviewTab
from furnace.screens.processes import ProcessesTab
from furnace.screens.network import NetworkTab
from furnace.screens.charos import CharosTab


class FurnaceApp(App):
    """CHAROS system monitor."""

    TITLE = "FURNACE"
    SUB_TITLE = "CHAROS System Monitor"
    CSS_PATH = Path(__file__).parent / "css" / "monitor.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("1", "tab_1", "Overview", show=True),
        Binding("2", "tab_2", "Processes", show=True),
        Binding("3", "tab_3", "Network", show=True),
        Binding("4", "tab_4", "CHAROS", show=True),
        Binding("slash", "focus_filter", "Filter", show=False),
    ]

    def __init__(self):
        super().__init__()
        self._collector = Collector()
        self._tick = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="overview"):
            with TabPane("🔥 Overview", id="overview"):
                yield OverviewTab(id="overview-tab")
            with TabPane("📋 Processes", id="processes"):
                yield ProcessesTab(id="processes-tab")
            with TabPane("🌐 Network", id="network"):
                yield NetworkTab(id="network-tab")
            with TabPane("🏠 CHAROS", id="charos"):
                yield CharosTab(id="charos-tab")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_data)
        # Kick off first CHAROS collection
        self._collect_charos()

    def _tick_data(self) -> None:
        self._tick += 1
        include_procs = (self._tick % 3 == 0)

        snap = self._collector.collect(include_processes=include_procs)

        # Always update overview + network
        self.query_one("#overview-tab", OverviewTab).update_data(snap)
        self.query_one("#network-tab", NetworkTab).update_data(snap)

        # Update processes every 3 ticks
        if include_procs:
            self.query_one("#processes-tab", ProcessesTab).update_data(snap.processes)

        # Update CHAROS every 10 ticks
        if self._tick % 10 == 0:
            self._collect_charos()

    @work(thread=False)
    async def _collect_charos(self) -> None:
        try:
            status = await collect_charos()
            self.query_one("#charos-tab", CharosTab).update_data(status)
        except Exception:
            pass

    def action_tab_1(self) -> None:
        self.query_one(TabbedContent).active = "overview"

    def action_tab_2(self) -> None:
        self.query_one(TabbedContent).active = "processes"

    def action_tab_3(self) -> None:
        self.query_one(TabbedContent).active = "network"

    def action_tab_4(self) -> None:
        self.query_one(TabbedContent).active = "charos"

    def action_focus_filter(self) -> None:
        try:
            inp = self.query_one("#proc-filter")
            inp.focus()
        except Exception:
            pass
