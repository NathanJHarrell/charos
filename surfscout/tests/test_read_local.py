"""Day 1 fast tests for Tool 1 (`surfscout read`).

Serves a local fixture HTML over a tiny pytest-httpserver and verifies that
`read_url_async` extracts the expected content as clean markdown.

Tests in this module are deterministic and offline-safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from surfscout.read import read_url_async

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample.html"


@pytest.fixture
def fixture_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def served_url(httpserver: HTTPServer, fixture_html: str) -> str:
    httpserver.expect_request("/listing").respond_with_data(
        fixture_html, content_type="text/html; charset=utf-8"
    )
    return httpserver.url_for("/listing")


async def test_read_returns_dict_with_required_keys(served_url: str):
    result = await read_url_async(served_url, settle_ms=200, timeout_ms=10_000)
    assert isinstance(result, dict)
    for key in ("url", "title", "markdown", "extraction_method", "char_count"):
        assert key in result, f"missing key: {key}"


async def test_read_extracts_listing_content(served_url: str):
    result = await read_url_async(served_url, settle_ms=200, timeout_ms=10_000)
    md = result["markdown"]
    # Core content should make it through
    assert "50.2 Acres in Costilla County" in md, "title not in markdown"
    assert "$89,500" in md, "price not in markdown"
    assert "Sangre de Cristo" in md, "description prose not in markdown"


async def test_read_strips_nav_and_footer(served_url: str):
    result = await read_url_async(served_url, settle_ms=200, timeout_ms=10_000)
    md = result["markdown"]
    # markdownify_only fallback strips these via its strip= list; readability
    # paths should also exclude them. Any extraction method should yield this.
    assert "Ad slot" not in md, "aside content leaked into markdown"
    assert "© 2026 SurfScout Test Fixtures" not in md, "footer leaked into markdown"


async def test_read_uses_some_extraction_method(served_url: str):
    result = await read_url_async(served_url, settle_ms=200, timeout_ms=10_000)
    assert result["extraction_method"] in {
        "readability_js",
        "readability_lxml",
        "markdownify_only",
    }


async def test_read_title_populated(served_url: str):
    result = await read_url_async(served_url, settle_ms=200, timeout_ms=10_000)
    # Either page <title> or Readability-extracted title should populate
    assert result["title"], "expected non-empty title"
