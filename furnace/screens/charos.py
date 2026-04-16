"""CHAROS tab — family infrastructure status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget

from furnace.widgets.charos_panel import CharosPanel
from furnace.data.charos_collector import CharosStatus


class CharosTab(Widget):

    DEFAULT_CSS = """
    CharosTab {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield CharosPanel(id="charos-panel")

    def update_data(self, status: CharosStatus) -> None:
        self.query_one("#charos-panel", CharosPanel).update_status(status)
