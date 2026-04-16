"""Rolling sparkline chart widget using block characters."""

from __future__ import annotations

from collections import deque

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


BLOCKS = " ▁▂▃▄▅▆▇█"


class SparklineChart(Widget):
    """A rolling sparkline that displays the last N values as a vertical bar chart."""

    DEFAULT_CSS = """
    SparklineChart {
        height: 6;
        padding: 0 1;
    }
    SparklineChart .spark-label {
        height: 1;
        text-style: bold;
    }
    SparklineChart .spark-value {
        height: 1;
        text-align: right;
    }
    SparklineChart .spark-graph {
        height: 4;
    }
    """

    def __init__(
        self,
        label: str = "",
        icon: str = "",
        max_values: int = 60,
        max_val: float = 100.0,
        unit: str = "%",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.label = label
        self.icon = icon
        self._values: deque[float] = deque(maxlen=max_values)
        self._max_val = max_val
        self._unit = unit

    def compose(self) -> ComposeResult:
        yield Static(f"{self.icon} {self.label}", classes="spark-label")
        yield Static("", classes="spark-value", id=f"val-{self.id or 'x'}")
        yield Static("", classes="spark-graph", id=f"graph-{self.id or 'x'}")

    def push_value(self, value: float) -> None:
        self._values.append(value)
        self._render_graph()

    def _render_graph(self) -> None:
        if not self._values:
            return

        # Update current value display
        current = self._values[-1]
        val_widget = self.query_one(f"#val-{self.id or 'x'}", Static)
        if self._unit == "B/s":
            val_widget.update(f"{_human_bytes(current)}/s")
        else:
            val_widget.update(f"{current:.1f}{self._unit}")

        # Build multi-line graph (4 rows tall)
        graph_widget = self.query_one(f"#graph-{self.id or 'x'}", Static)
        width = max(self.size.width - 2, 10)
        values = list(self._values)

        # Pad or trim to fill width
        if len(values) < width:
            values = [0.0] * (width - len(values)) + values
        else:
            values = values[-width:]

        # Auto-scale max for non-percentage values
        max_val = self._max_val
        if self._unit != "%":
            peak = max(values) if values else 1.0
            max_val = max(peak * 1.2, 1.0)

        # Normalize to 0-1
        normalized = [min(v / max_val, 1.0) if max_val > 0 else 0 for v in values]

        # Render 4 rows (each row represents 25% of the range)
        rows = 4
        lines = []
        for row in range(rows):
            row_top = 1.0 - (row / rows)
            row_bottom = 1.0 - ((row + 1) / rows)
            line = ""
            for val in normalized:
                if val >= row_top:
                    line += "█"
                elif val > row_bottom:
                    frac = (val - row_bottom) / (row_top - row_bottom)
                    idx = int(frac * (len(BLOCKS) - 1))
                    line += BLOCKS[idx]
                else:
                    line += " "
            lines.append(line)

        graph_widget.update("\n".join(lines))


def _human_bytes(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"
