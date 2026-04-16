"""Charizard ASCII art watermark."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Static


ASSET_PATH = Path(__file__).parent.parent / "assets" / "charizard.txt"


class CharizardWatermark(Static):
    """Faded Charizard silhouette behind the overview tab."""

    DEFAULT_CSS = """
    CharizardWatermark {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
    }
    """

    def on_mount(self) -> None:
        try:
            art = ASSET_PATH.read_text()
            self.update(art)
        except FileNotFoundError:
            self.update("")
