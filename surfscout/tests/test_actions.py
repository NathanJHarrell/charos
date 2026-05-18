"""Day 3 — round-trip every action primitive against a local fixture page.

Spins up a single headless daemon (session name `test-actions`) at module
scope, serves the interactive fixture via pytest-httpserver, and exercises each
handler through the real IPC layer.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from surfscout.ipc import profile_dir, send_request_sync
from surfscout.session import start, stop

SESSION_NAME = "test-actions"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "interactive.html"
FIXTURE_URL = FIXTURE_PATH.resolve().as_uri()  # file:///.../interactive.html


def _send(method: str, args: dict | None = None):
    return send_request_sync(method, args or {}, session_name=SESSION_NAME, timeout=10.0)


@pytest.fixture(scope="module")
def daemon():
    # Wipe any leftover profile from prior runs for reproducibility
    profile = profile_dir(SESSION_NAME)
    if profile.exists():
        shutil.rmtree(profile)

    result = start(name=SESSION_NAME, headless=True)
    if not result.get("started") and not result.get("already_running"):
        pytest.fail(f"daemon failed to start: {result}")

    yield

    stop(name=SESSION_NAME)


@pytest.fixture(autouse=True)
def navigate_to_fixture(daemon):
    """Reset every test to a fresh load of the fixture page."""
    _send("navigate", {"url": FIXTURE_URL, "wait_until": "load"})


# ────────────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────────────


def test_ping():
    result = _send("ping")
    assert result["ok"] is True
    assert "pid" in result


def test_get_url():
    assert _send("get_url") == FIXTURE_URL


def test_click_selector_increments_counter():
    _send("click_selector", {"selector": "#click-btn"})
    _send("click_selector", {"selector": "#click-btn"})
    _send("click_selector", {"selector": "#click-btn"})
    counter_text = _send("get_dom_text", {"selector": "#click-counter"})
    assert counter_text.strip() == "3"


def test_click_at_coordinates():
    elements = _send("get_elements", {"selector": "#click-btn"})
    assert elements, "expected click-btn to be findable"
    bbox = elements[0]["bbox"]
    cx = int(bbox["x"] + bbox["width"] / 2)
    cy = int(bbox["y"] + bbox["height"] / 2)
    _send("click", {"x": cx, "y": cy})
    counter_text = _send("get_dom_text", {"selector": "#click-counter"})
    assert counter_text.strip() == "1"


def test_type_into_selector():
    _send("type", {"text": "hello scout", "selector": "#text-input"})
    output = _send("get_dom_text", {"selector": "#typed-output"})
    assert output.strip() == "hello scout"


def test_key_press_logs():
    _send("click_selector", {"selector": "#key-input"})
    _send("key", {"name": "ArrowDown"})
    _send("key", {"name": "Enter"})
    log = _send("get_dom_text", {"selector": "#key-log"})
    assert "ArrowDown" in log
    assert "Enter" in log


def test_select_dropdown():
    result = _send("select", {"selector": "#dropdown", "value": "gamma"})
    assert result["selected"] == ["gamma"]
    output = _send("get_dom_text", {"selector": "#dropdown-output"})
    assert output.strip() == "gamma"


def test_scroll_changes_scroll_y():
    before = _send("eval", {"js": "window.scrollY"})
    result = _send("scroll", {"direction": "down", "amount": 800})
    after = _send("eval", {"js": "window.scrollY"})
    assert after > before
    assert result["scroll_y"] == after


def test_wait_returns_immediately():
    result = _send("wait", {"ms": 50})
    assert result["waited_ms"] == 50


def test_wait_for_delayed_element():
    _send("click_selector", {"selector": "#trigger-delayed"})
    _send("wait_for", {"selector": "#delayed", "state": "visible", "timeout_ms": 2000})
    text = _send("get_dom_text", {"selector": "#delayed"})
    assert "delayed-element" in text


def test_hover_reveals_element():
    _send("hover", {"selector": ".hover-target"})
    _send("wait", {"ms": 50})
    style_display = _send("eval", {"js": "getComputedStyle(document.getElementById('hover-reveal')).display"})
    assert style_display == "block"


def test_viewport_resize():
    result = _send("viewport", {"width": 1024, "height": 600})
    assert result == {"width": 1024, "height": 600}
    inner = _send("eval", {"js": "[window.innerWidth, window.innerHeight]"})
    assert inner == [1024, 600]


def test_eval_returns_value():
    result = _send("eval", {"js": "1 + 1"})
    assert result == 2
    title = _send("eval", {"js": "document.getElementById('page-title').textContent"})
    assert "Day 3" in title


def test_get_elements_returns_list_with_bboxes():
    items = _send("get_elements", {"selector": "li.item"})
    assert len(items) == 4
    texts = [item["text"].strip() for item in items]
    assert texts == ["item-A", "item-B", "item-C", "item-D"]
    for item in items:
        assert item["tag"] == "li"
        assert item["bbox"] is not None
        assert "x" in item["bbox"] and "width" in item["bbox"]


def test_back_and_forward():
    # Navigate somewhere else, then back, then forward
    _send("navigate", {"url": "about:blank"})
    assert _send("get_url") == "about:blank"
    _send("back")
    assert _send("get_url") == FIXTURE_URL
    _send("forward")
    assert _send("get_url") == "about:blank"


def test_screenshot_writes_file(tmp_path):
    out = tmp_path / "shot.png"
    result = _send("screenshot", {"path": str(out), "full_page": False})
    assert result["path"] == str(out)
    assert out.exists() and out.stat().st_size > 0


def test_daemon_read_handler():
    """Day 4: daemon `read` handler runs Tool 1 pipeline against persistent context."""
    sample_url = (Path(__file__).parent / "fixtures" / "sample.html").resolve().as_uri()
    result = _send("read", {"url": sample_url})
    assert result["url"] == sample_url
    assert result["title"]
    assert result["markdown"]
    assert result["extraction_method"] in (
        "readability_js",
        "readability_lxml",
        "markdownify_only",
    )
    assert "facts" in result
    assert result["char_count"] > 0
