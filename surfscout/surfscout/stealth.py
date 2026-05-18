"""Stealth integration — wraps playwright-stealth so the dependency is isolated.

If we ever swap stealth packages (e.g., to a different fingerprint patcher),
only this file changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext


async def apply_stealth(context: BrowserContext) -> None:
    """Apply stealth patches to a Playwright BrowserContext.

    Defeats most common bot-detection techniques:
    - navigator.webdriver = false
    - realistic user-agent + platform
    - chrome.runtime stub
    - WebGL/canvas fingerprint normalization
    - permission query patches

    This is the only place playwright-stealth is imported in the codebase.
    """
    try:
        from playwright_stealth import Stealth
    except ImportError as e:
        raise RuntimeError(
            "playwright-stealth is not installed. Run "
            "`.venv/bin/pip install playwright-stealth` to install."
        ) from e

    stealth = Stealth()
    await stealth.apply_stealth_async(context)
