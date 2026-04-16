"""Big-number stat card with Nerd Font icon."""

from __future__ import annotations

from textual.widgets import Static


class StatCard(Static):
    """Displays an icon, label, and big value."""

    DEFAULT_CSS = """
    StatCard {
        width: 1fr;
        height: 3;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        margin: 0 1;
        background: $surface;
    }
    """

    def __init__(self, icon: str = "", label: str = "", **kwargs):
        super().__init__(**kwargs)
        self.icon = icon
        self.label = label
        self._value = "..."

    def set_value(self, value: str) -> None:
        self._value = value
        self.update(f"{self.icon} {self.label}\n{self._value}")
