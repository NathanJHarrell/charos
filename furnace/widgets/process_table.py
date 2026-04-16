"""Sortable, filterable process table."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Input

from furnace.data.collector import ProcessInfo


class ProcessTable(Widget):
    """Process list with search filter and sortable columns."""

    DEFAULT_CSS = """
    ProcessTable {
        height: 1fr;
    }
    ProcessTable Input {
        height: 3;
        margin: 0 0 1 0;
    }
    ProcessTable DataTable {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._processes: list[ProcessInfo] = []
        self._filter: str = ""
        self._sort_key: str = "cpu_percent"
        self._sort_reverse: bool = True

    def compose(self) -> ComposeResult:
        yield Input(placeholder=" Filter processes...", id="proc-filter")
        table = DataTable(id="proc-table")
        table.cursor_type = "row"
        table.zebra_stripes = True
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#proc-table", DataTable)
        table.add_columns("PID", "Name", "User", "CPU%", "MEM%", "Status")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "proc-filter":
            self._filter = event.value.lower()
            self._refresh_table()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col_map = {0: "pid", 1: "name", 2: "username", 3: "cpu_percent", 4: "memory_percent", 5: "status"}
        key = col_map.get(event.column_index, "cpu_percent")
        if key == self._sort_key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = key in ("cpu_percent", "memory_percent", "pid")
        self._refresh_table()

    def update_processes(self, processes: list[ProcessInfo]) -> None:
        self._processes = processes
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#proc-table", DataTable)
        table.clear()

        filtered = self._processes
        if self._filter:
            filtered = [p for p in filtered if self._filter in p.name.lower()]

        sorted_procs = sorted(
            filtered,
            key=lambda p: getattr(p, self._sort_key, 0) or 0,
            reverse=self._sort_reverse,
        )

        for proc in sorted_procs[:200]:  # cap at 200 rows for performance
            table.add_row(
                str(proc.pid),
                proc.name[:25],
                proc.username[:10],
                f"{proc.cpu_percent:.1f}",
                f"{proc.memory_percent:.1f}",
                proc.status[:8],
            )
