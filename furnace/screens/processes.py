"""Processes tab — filterable, sortable process list."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget

from furnace.widgets.process_table import ProcessTable
from furnace.data.collector import ProcessInfo


class ProcessesTab(Widget):

    DEFAULT_CSS = """
    ProcessesTab {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield ProcessTable(id="process-table")

    def update_data(self, processes: list[ProcessInfo]) -> None:
        self.query_one("#process-table", ProcessTable).update_processes(processes)
