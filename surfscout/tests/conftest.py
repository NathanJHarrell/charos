"""Pytest configuration — discovers Nix-managed playwright-chromium on NixOS.

The bin/surfscout shim sets SURFSCOUT_CHROMIUM_PATH for runtime invocations,
but pytest bypasses the shim. This conftest applies the same discovery so
tests are self-contained on tc-nest. On non-NixOS hosts the glob misses,
the env var stays unset, and Playwright uses its bundled Chromium.

See: ~/Manor/Scout/vault/NixOS_Playwright_pip_browser_shared_library_fix.md
"""

from __future__ import annotations

import glob
import os


def _discover_nix_chromium() -> str | None:
    for candidate in sorted(glob.glob("/nix/store/*-playwright-chromium/chrome-linux/chrome")):
        if os.access(candidate, os.X_OK):
            return candidate
    return None


if not os.environ.get("SURFSCOUT_CHROMIUM_PATH"):
    found = _discover_nix_chromium()
    if found:
        os.environ["SURFSCOUT_CHROMIUM_PATH"] = found
