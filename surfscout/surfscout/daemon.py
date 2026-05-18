"""SurfScout daemon — owns the persistent Playwright browser session.

Listens on a Unix domain socket at ~/.surfscout/sock-<name>. Each connection
sends a single newline-delimited JSON request and receives a single
newline-delimited JSON response, then closes.

Mirrors the clipd/nest_daemon.py pattern. Adapted for UDS + method dispatch.

Day 1 scope: ping, navigate, get_url, get_dom_text, screenshot.
Day 3 will add the rest of the action primitives (click, type, key, scroll,
hover, select, viewport, eval, wait, wait_for, click_selector, get_elements,
back, forward).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from surfscout.ipc import (
    DEFAULT_SESSION_NAME,
    ensure_state_dir,
    profile_dir,
    socket_path,
)
from surfscout.stealth import apply_stealth

# Type alias for handler signature
Handler = Callable[["DaemonState", dict[str, Any]], Awaitable[Any]]


class DaemonState:
    """Holds the live Playwright objects for the daemon's lifetime."""

    def __init__(self, browser: Browser, context: BrowserContext, page: Page):
        self.browser = browser
        self.context = context
        self.page = page
        self.started_at = time.time()
        self.last_activity = time.time()


# ────────────────────────────────────────────────────────────────────────────
# Handler registry
# ────────────────────────────────────────────────────────────────────────────

HANDLERS: dict[str, Handler] = {}


def register(method: str):
    """Decorator: register a handler under a method name."""

    def decorator(func: Handler) -> Handler:
        HANDLERS[method] = func
        return func

    return decorator


# ────────────────────────────────────────────────────────────────────────────
# Day 1 handlers
# ────────────────────────────────────────────────────────────────────────────


@register("ping")
async def handle_ping(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Health check — confirms daemon is alive and responsive."""
    return {
        "ok": True,
        "pid": os.getpid(),
        "uptime_sec": round(time.time() - state.started_at, 2),
        "current_url": state.page.url,
    }


@register("navigate")
async def handle_navigate(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Navigate to a URL.

    args: {"url": str, "wait_until": "domcontentloaded"|"load"|"networkidle" (default: domcontentloaded)}
    """
    url = args["url"]
    wait_until = args.get("wait_until", "domcontentloaded")
    response = await state.page.goto(url, wait_until=wait_until)
    return {
        "url": state.page.url,
        "status": response.status if response else None,
    }


@register("get_url")
async def handle_get_url(state: DaemonState, args: dict[str, Any]) -> str:
    """Return the current page URL."""
    return state.page.url


@register("get_dom_text")
async def handle_get_dom_text(state: DaemonState, args: dict[str, Any]) -> str:
    """Return visible text from the page (or from a selector if given).

    args: {"selector": str | None}
    """
    selector = args.get("selector")
    if selector:
        elements = await state.page.query_selector_all(selector)
        texts = []
        for el in elements:
            text = await el.inner_text()
            texts.append(text)
        return "\n\n".join(texts)
    return await state.page.evaluate("document.body.innerText")


@register("screenshot")
async def handle_screenshot(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Take a screenshot. Returns the path it was written to.

    args: {"path": str | None, "full_page": bool (default False)}
    """
    path = args.get("path")
    full_page = args.get("full_page", False)
    if not path:
        ts = int(time.time() * 1000)
        path = f"/tmp/surfscout-shot-{ts}.png"
    await state.page.screenshot(path=path, full_page=full_page)
    return {"path": path}


# ────────────────────────────────────────────────────────────────────────────
# Day 3 action primitives
# ────────────────────────────────────────────────────────────────────────────


@register("click")
async def handle_click(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Click at viewport coordinates.

    args: {"x": int, "y": int, "button": "left"|"right"|"middle" (default left)}
    """
    x = int(args["x"])
    y = int(args["y"])
    button = args.get("button", "left")
    await state.page.mouse.click(x, y, button=button)
    return {"clicked_at": [x, y], "button": button, "url": state.page.url}


@register("click_selector")
async def handle_click_selector(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Click an element matching a CSS selector.

    args: {"selector": str, "timeout_ms": int (default 5000)}
    """
    selector = args["selector"]
    timeout = args.get("timeout_ms", 5000)
    await state.page.click(selector, timeout=timeout)
    return {"clicked": selector, "url": state.page.url}


@register("type")
async def handle_type(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Type text into the focused element (or a selector if given).

    args: {"text": str, "selector": str | None, "delay_ms": int (default 0)}
    """
    text = args["text"]
    selector = args.get("selector")
    delay = args.get("delay_ms", 0)
    if selector:
        await state.page.fill(selector, "")  # clear first
        await state.page.type(selector, text, delay=delay)
    else:
        await state.page.keyboard.type(text, delay=delay)
    return {"typed_chars": len(text), "selector": selector}


@register("key")
async def handle_key(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Press a named key (Enter, Tab, Escape, ArrowDown, etc.).

    args: {"name": str}
    """
    name = args["name"]
    await state.page.keyboard.press(name)
    return {"pressed": name, "url": state.page.url}


@register("scroll")
async def handle_scroll(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Scroll the page in a direction by N pixels (default 500).

    args: {"direction": "up"|"down"|"left"|"right", "amount": int (default 500)}
    """
    direction = args.get("direction", "down")
    amount = int(args.get("amount", 500))
    deltas = {
        "up": (0, -amount),
        "down": (0, amount),
        "left": (-amount, 0),
        "right": (amount, 0),
    }
    if direction not in deltas:
        raise ValueError(f"unknown direction: {direction!r}")
    dx, dy = deltas[direction]
    await state.page.evaluate(f"window.scrollBy({dx}, {dy})")
    new_y = await state.page.evaluate("window.scrollY")
    return {"direction": direction, "amount": amount, "scroll_y": new_y}


@register("wait")
async def handle_wait(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Sleep for N milliseconds.

    args: {"ms": int}
    """
    ms = int(args["ms"])
    await state.page.wait_for_timeout(ms)
    return {"waited_ms": ms}


@register("wait_for")
async def handle_wait_for(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Wait for a selector to reach a state.

    args: {"selector": str, "timeout_ms": int (default 10000),
           "state": "attached"|"detached"|"visible"|"hidden" (default visible)}
    """
    selector = args["selector"]
    timeout = args.get("timeout_ms", 10000)
    target_state = args.get("state", "visible")
    await state.page.wait_for_selector(selector, timeout=timeout, state=target_state)
    return {"selector": selector, "state": target_state}


@register("hover")
async def handle_hover(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Hover over a selector or coordinate pair.

    args: either {"selector": str} or {"x": int, "y": int}
    """
    if "selector" in args and args["selector"]:
        await state.page.hover(args["selector"])
        return {"hovered": args["selector"]}
    x_raw = args.get("x")
    y_raw = args.get("y")
    if x_raw is None or y_raw is None:
        raise ValueError("hover requires either 'selector' or both 'x' and 'y' coordinates")
    try:
        x = int(x_raw)
        y = int(y_raw)
    except (TypeError, ValueError) as e:
        raise ValueError(f"hover coordinates must be ints: {e}") from e
    await state.page.mouse.move(x, y)
    return {"hovered_at": [x, y]}


@register("select")
async def handle_select(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Select an option in a native <select> dropdown by value.

    args: {"selector": str, "value": str | list[str]}
    """
    selector = args["selector"]
    value = args["value"]
    selected = await state.page.select_option(selector, value=value)
    return {"selector": selector, "selected": selected}


@register("viewport")
async def handle_viewport(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Resize the viewport.

    args: {"width": int, "height": int}
    """
    width = int(args["width"])
    height = int(args["height"])
    await state.page.set_viewport_size({"width": width, "height": height})
    return {"width": width, "height": height}


@register("eval")
async def handle_eval(state: DaemonState, args: dict[str, Any]) -> Any:
    """Evaluate arbitrary JavaScript in the page context. Last-resort escape.

    args: {"js": str}
    Returns whatever the JS evaluates to (must be JSON-serializable).
    """
    js = args["js"]
    return await state.page.evaluate(js)


@register("get_elements")
async def handle_get_elements(
    state: DaemonState, args: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return matching elements with selectors, bounding boxes, and text snippets.

    args: {"selector": str, "limit": int (default 50)}
    """
    selector = args["selector"]
    limit = int(args.get("limit", 50))
    elements = await state.page.query_selector_all(selector)
    out: list[dict[str, Any]] = []
    for i, el in enumerate(elements[:limit]):
        try:
            box = await el.bounding_box()
        except Exception:
            box = None
        try:
            text = (await el.inner_text())[:200]
        except Exception:
            text = ""
        try:
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
        except Exception:
            tag = None
        out.append({
            "index": i,
            "tag": tag,
            "text": text,
            "bbox": box,  # {"x", "y", "width", "height"} or None
        })
    return out


@register("read")
async def handle_read(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Tool 1's pipeline against the warmed persistent context.

    Use this when a site WAF blocks the ephemeral Tool 1 — open the daemon
    in headed mode, click through the challenge once, then call this handler
    for subsequent reads. Cookies + fingerprint persist in the profile dir.

    args: {"url": str, "settle_ms": int (default 1500),
           "timeout_ms": int (default 30000)}
    """
    from surfscout.read import DEFAULT_SETTLE_MS, DEFAULT_TIMEOUT_MS, extract_from_page

    url = args["url"]
    settle_ms = int(args.get("settle_ms", DEFAULT_SETTLE_MS))
    timeout_ms = int(args.get("timeout_ms", DEFAULT_TIMEOUT_MS))
    use_readability = bool(args.get("use_readability", True))
    await state.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    return await extract_from_page(
        state.page, settle_ms=settle_ms, use_readability=use_readability
    )


@register("back")
async def handle_back(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Go back one step in history."""
    response = await state.page.go_back()
    return {
        "url": state.page.url,
        "status": response.status if response else None,
    }


@register("forward")
async def handle_forward(state: DaemonState, args: dict[str, Any]) -> dict[str, Any]:
    """Go forward one step in history."""
    response = await state.page.go_forward()
    return {
        "url": state.page.url,
        "status": response.status if response else None,
    }


# ────────────────────────────────────────────────────────────────────────────
# Connection handling
# ────────────────────────────────────────────────────────────────────────────


async def handle_connection(
    state: DaemonState,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """Handle a single client connection: read one request, send one response."""
    try:
        line = await reader.readline()
        if not line:
            return

        try:
            request = json.loads(line.decode("utf-8").rstrip("\n"))
        except json.JSONDecodeError as e:
            response = {"ok": False, "error": f"invalid JSON: {e}"}
        else:
            method = request.get("method")
            args = request.get("args", {})
            handler = HANDLERS.get(method)
            if handler is None:
                response = {"ok": False, "error": f"unknown method: {method}"}
            else:
                try:
                    result = await handler(state, args)
                    state.last_activity = time.time()
                    response = {"ok": True, "result": result}
                except Exception as e:
                    response = {
                        "ok": False,
                        "error": f"{type(e).__name__}: {e}",
                    }

        writer.write((json.dumps(response) + "\n").encode("utf-8"))
        await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────────────
# Daemon lifecycle
# ────────────────────────────────────────────────────────────────────────────


async def run_daemon(session_name: str = DEFAULT_SESSION_NAME, headless: bool = False) -> None:
    """Main daemon loop: launch browser, accept connections, clean up on exit."""
    ensure_state_dir()
    sock_path = socket_path(session_name)
    profile = profile_dir(session_name)
    profile.mkdir(parents=True, exist_ok=True)

    # Display check (headed mode requires X or Wayland)
    if not headless:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            print(
                "surfscout daemon: no display detected ($DISPLAY or $WAYLAND_DISPLAY). "
                "Launch with --headless or run from a graphical session.",
                file=sys.stderr,
            )
            sys.exit(2)

    # If a stale socket exists, remove it (we already verified no daemon is alive
    # via session.start() before we got here)
    if sock_path.exists():
        sock_path.unlink()

    # Honor SURFSCOUT_CHROMIUM_PATH — set by the bin/surfscout shim on NixOS
    # to point at a Nix-managed playwright-chromium (rpath-linked). On other
    # distros this is unset and Playwright uses its bundled browser.
    chromium_path = os.environ.get("SURFSCOUT_CHROMIUM_PATH") or None

    # Reuse Tool 1's realistic context dressing so the daemon's first cold
    # request to a WAF-protected site doesn't get 403'd before the profile
    # has any cookies. End-to-end test surfaced this: Tool 1 ephemeral
    # passed LandWatch's Akamai; cold daemon failed without the dressing.
    from surfscout.read import (
        REALISTIC_HEADERS,
        REALISTIC_LOCALE,
        REALISTIC_TIMEZONE,
        REALISTIC_USER_AGENT,
    )

    async with async_playwright() as pw:
        # Persistent context = profile, cookies, logins all persist
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(profile),
            "headless": headless,
            "viewport": {"width": 1280, "height": 800},
            "user_agent": REALISTIC_USER_AGENT,
            "locale": REALISTIC_LOCALE,
            "timezone_id": REALISTIC_TIMEZONE,
            "extra_http_headers": REALISTIC_HEADERS,
        }
        if chromium_path:
            launch_kwargs["executable_path"] = chromium_path
        context = await pw.chromium.launch_persistent_context(**launch_kwargs)
        await apply_stealth(context)

        # Use the first page (persistent context always has one)
        page = context.pages[0] if context.pages else await context.new_page()
        # Browser is the launcher; with launch_persistent_context, the context
        # IS the entry point. We don't have a separate Browser handle here,
        # so we pass None for the Browser slot and rely on context for cleanup.
        state = DaemonState(browser=None, context=context, page=page)  # type: ignore[arg-type]

        # Start the UDS server
        server = await asyncio.start_unix_server(
            lambda r, w: handle_connection(state, r, w),
            path=str(sock_path),
        )
        # Tighten socket permissions (user-only)
        os.chmod(sock_path, 0o600)

        # Set up clean shutdown on SIGTERM/SIGINT
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def request_stop(*_):
            stop_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, request_stop)

        print(f"surfscout daemon: listening on {sock_path} (PID {os.getpid()})")

        # Run until signaled
        async with server:
            stop_task = asyncio.create_task(stop_event.wait())
            await stop_task

        # Clean up
        print("surfscout daemon: shutting down")
        try:
            await context.close()
        except Exception:
            pass
        if sock_path.exists():
            sock_path.unlink()


def main() -> None:
    """Entry point when run as `python -m surfscout.daemon`."""
    import argparse

    parser = argparse.ArgumentParser(description="SurfScout daemon (long-running)")
    parser.add_argument("--name", default=DEFAULT_SESSION_NAME, help="session name")
    parser.add_argument("--headless", action="store_true", help="headless browser")
    args = parser.parse_args()

    try:
        asyncio.run(run_daemon(session_name=args.name, headless=args.headless))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
