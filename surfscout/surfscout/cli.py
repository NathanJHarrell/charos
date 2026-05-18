"""SurfScout CLI — argparse with subparsers for read, session, and action primitives.

Day 1 scope: read, session start/stop/status, ping, navigate, get-url,
get-dom-text, screenshot.

Day 3 added: click, click-selector, type, key, scroll, hover, select,
viewport, eval, wait, wait-for, back, forward, get-elements.

Output convention: action subcommands print JSON to stdout (forward-compat
for the aspirational `surfscout/reason/` headless-batch module). The `read`
subcommand prints markdown to stdout (it's the natural human-and-LLM format).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from surfscout import __version__
from surfscout.ipc import DEFAULT_SESSION_NAME, IPCError, send_request_sync


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2))


def _send(method: str, args: dict[str, Any] | None = None, *, name: str = DEFAULT_SESSION_NAME) -> None:
    """Send an IPC request, print result as JSON, exit nonzero on error."""
    try:
        result = send_request_sync(method, args or {}, session_name=name)
        _print_json({"ok": True, "result": result})
    except IPCError as e:
        _print_json({"ok": False, "error": str(e)})
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ────────────────────────────────────────────────────────────────────────────


def cmd_read(args: argparse.Namespace) -> None:
    """Tool 1 — render URL to markdown.

    Default: standalone ephemeral browser (stateless).
    With --use-daemon: routes through the warmed persistent context (lets
    you bypass WAF / use logged-in cookies). Daemon must be running.
    """
    use_readability = not args.no_readability
    if args.use_daemon:
        try:
            result = send_request_sync(
                "read",
                {
                    "url": args.url,
                    "settle_ms": args.settle_ms,
                    "timeout_ms": args.timeout_ms,
                    "use_readability": use_readability,
                },
                session_name=args.session,
                timeout=max(60.0, (args.timeout_ms / 1000.0) + 30.0),
            )
        except IPCError as e:
            _print_json({"ok": False, "error": str(e)})
            sys.exit(1)
    else:
        from surfscout.read import read_url

        result = read_url(
            args.url,
            settle_ms=args.settle_ms,
            timeout_ms=args.timeout_ms,
            headless=args.headless,
            use_readability=use_readability,
        )

    if args.json:
        _print_json(result)
    else:
        # Human/LLM-friendly default: just print markdown to stdout
        sys.stdout.write(result["markdown"])
        if not result["markdown"].endswith("\n"):
            sys.stdout.write("\n")


def cmd_session_start(args: argparse.Namespace) -> None:
    from surfscout.session import start

    result = start(name=args.name, headless=args.headless)
    _print_json(result)
    if not result.get("started") and not result.get("already_running"):
        sys.exit(1)


def cmd_session_stop(args: argparse.Namespace) -> None:
    from surfscout.session import stop

    result = stop(name=args.name)
    _print_json(result)


def cmd_session_status(args: argparse.Namespace) -> None:
    from surfscout.session import status

    result = status(name=args.name)
    _print_json(result)


# Action primitive handlers (thin IPC wrappers)


def cmd_ping(args: argparse.Namespace) -> None:
    _send("ping", name=args.name)


def cmd_navigate(args: argparse.Namespace) -> None:
    _send("navigate", {"url": args.url, "wait_until": args.wait_until}, name=args.name)


def cmd_get_url(args: argparse.Namespace) -> None:
    _send("get_url", name=args.name)


def cmd_get_dom_text(args: argparse.Namespace) -> None:
    _send("get_dom_text", {"selector": args.selector}, name=args.name)


def cmd_screenshot(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {"full_page": args.full_page}
    if args.path:
        payload["path"] = args.path
    _send("screenshot", payload, name=args.name)


# Day 3 action primitives ----------------------------------------------------


def cmd_click(args: argparse.Namespace) -> None:
    _send("click", {"x": args.x, "y": args.y, "button": args.button}, name=args.name)


def cmd_click_selector(args: argparse.Namespace) -> None:
    _send(
        "click_selector",
        {"selector": args.selector, "timeout_ms": args.timeout_ms},
        name=args.name,
    )


def cmd_type(args: argparse.Namespace) -> None:
    _send(
        "type",
        {"text": args.text, "selector": args.selector, "delay_ms": args.delay_ms},
        name=args.name,
    )


def cmd_key(args: argparse.Namespace) -> None:
    _send("key", {"name": args.key_name}, name=args.name)


def cmd_scroll(args: argparse.Namespace) -> None:
    _send(
        "scroll",
        {"direction": args.direction, "amount": args.amount},
        name=args.name,
    )


def cmd_wait(args: argparse.Namespace) -> None:
    _send("wait", {"ms": args.ms}, name=args.name)


def cmd_wait_for(args: argparse.Namespace) -> None:
    _send(
        "wait_for",
        {"selector": args.selector, "timeout_ms": args.timeout_ms, "state": args.state},
        name=args.name,
    )


def cmd_hover(args: argparse.Namespace) -> None:
    if args.selector:
        payload = {"selector": args.selector}
    else:
        payload = {"x": args.x, "y": args.y}
    _send("hover", payload, name=args.name)


def cmd_select(args: argparse.Namespace) -> None:
    _send(
        "select",
        {"selector": args.selector, "value": args.value},
        name=args.name,
    )


def cmd_viewport(args: argparse.Namespace) -> None:
    _send(
        "viewport",
        {"width": args.width, "height": args.height},
        name=args.name,
    )


def cmd_eval(args: argparse.Namespace) -> None:
    _send("eval", {"js": args.js}, name=args.name)


def cmd_get_elements(args: argparse.Namespace) -> None:
    _send(
        "get_elements",
        {"selector": args.selector, "limit": args.limit},
        name=args.name,
    )


def cmd_back(args: argparse.Namespace) -> None:
    _send("back", name=args.name)


def cmd_forward(args: argparse.Namespace) -> None:
    _send("forward", name=args.name)


# ────────────────────────────────────────────────────────────────────────────
# Parser construction
# ────────────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surfscout",
        description="Family-built browser automation. CLI primitives for Claude Code sessions.",
    )
    p.add_argument("--version", action="version", version=f"surfscout {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>")

    # read --------------------------------------------------------------------
    read_p = sub.add_parser(
        "read",
        help="render a URL and print clean markdown (standalone, no daemon)",
    )
    read_p.add_argument("url", help="URL to render")
    read_p.add_argument(
        "--settle-ms", type=int, default=1500,
        help="ms to wait after domcontentloaded before extraction",
    )
    read_p.add_argument(
        "--timeout-ms", type=int, default=30_000,
        help="overall navigation timeout",
    )
    read_p.add_argument(
        "--no-headless", dest="headless", action="store_false", default=True,
        help="show browser window (default: headless for read)",
    )
    read_p.add_argument(
        "--json", action="store_true",
        help="print full result as JSON instead of just the markdown",
    )
    read_p.add_argument(
        "--use-daemon", action="store_true",
        help="route through the warmed persistent context (daemon must be running)",
    )
    read_p.add_argument(
        "--session", default=DEFAULT_SESSION_NAME,
        help="session name (with --use-daemon)",
    )
    read_p.add_argument(
        "--no-readability", action="store_true",
        help="skip Readability extraction (preserves card grids on search-results pages)",
    )
    read_p.set_defaults(func=cmd_read)

    # session -----------------------------------------------------------------
    session_p = sub.add_parser("session", help="manage the persistent browser session")
    session_sub = session_p.add_subparsers(dest="session_cmd", required=True)

    sstart = session_sub.add_parser("start", help="spawn the daemon")
    sstart.add_argument("--name", default=DEFAULT_SESSION_NAME)
    sstart.add_argument("--headless", action="store_true")
    sstart.set_defaults(func=cmd_session_start)

    sstop = session_sub.add_parser("stop", help="stop the daemon")
    sstop.add_argument("--name", default=DEFAULT_SESSION_NAME)
    sstop.set_defaults(func=cmd_session_stop)

    sstatus = session_sub.add_parser("status", help="report daemon status")
    sstatus.add_argument("--name", default=DEFAULT_SESSION_NAME)
    sstatus.set_defaults(func=cmd_session_status)

    # action primitives (Day 1 subset) ----------------------------------------
    def _add_action(name: str, help_text: str, configure):
        ap = sub.add_parser(name, help=help_text)
        ap.add_argument("--name", default=DEFAULT_SESSION_NAME, help="session name")
        configure(ap)
        return ap

    def _config_ping(ap):
        ap.set_defaults(func=cmd_ping)

    def _config_navigate(ap):
        ap.add_argument("url", help="URL to navigate to")
        ap.add_argument(
            "--wait-until", default="domcontentloaded",
            choices=["domcontentloaded", "load", "networkidle"],
        )
        ap.set_defaults(func=cmd_navigate)

    def _config_get_url(ap):
        ap.set_defaults(func=cmd_get_url)

    def _config_get_dom_text(ap):
        ap.add_argument("selector", nargs="?", default=None,
                        help="CSS selector (omit for whole page text)")
        ap.set_defaults(func=cmd_get_dom_text)

    def _config_screenshot(ap):
        ap.add_argument("--path", default=None, help="output path (default: /tmp/surfscout-shot-*.png)")
        ap.add_argument("--full-page", action="store_true", help="capture full scrollable page")
        ap.set_defaults(func=cmd_screenshot)

    _add_action("ping", "round-trip a request to verify the daemon is alive", _config_ping)
    _add_action("navigate", "navigate to a URL", _config_navigate)
    _add_action("get-url", "print current page URL", _config_get_url)
    _add_action("get-dom-text", "print visible text in selector (or whole page)", _config_get_dom_text)
    _add_action("screenshot", "save a screenshot; print its path", _config_screenshot)

    # Day 3 action primitives -------------------------------------------------

    def _config_click(ap):
        ap.add_argument("x", type=int)
        ap.add_argument("y", type=int)
        ap.add_argument("--button", default="left", choices=["left", "right", "middle"])
        ap.set_defaults(func=cmd_click)

    def _config_click_selector(ap):
        ap.add_argument("selector")
        ap.add_argument("--timeout-ms", type=int, default=5000)
        ap.set_defaults(func=cmd_click_selector)

    def _config_type(ap):
        ap.add_argument("text")
        ap.add_argument("--selector", default=None,
                        help="optional: type into this element (else focused)")
        ap.add_argument("--delay-ms", type=int, default=0,
                        help="ms between keystrokes (0 = instant)")
        ap.set_defaults(func=cmd_type)

    def _config_key(ap):
        ap.add_argument("key_name", metavar="key",
                        help="key name (Enter, Tab, Escape, ArrowDown, ...)")
        ap.set_defaults(func=cmd_key)

    def _config_scroll(ap):
        ap.add_argument("direction", choices=["up", "down", "left", "right"])
        ap.add_argument("amount", type=int, nargs="?", default=500,
                        help="pixels to scroll (default 500)")
        ap.set_defaults(func=cmd_scroll)

    def _config_wait(ap):
        ap.add_argument("ms", type=int)
        ap.set_defaults(func=cmd_wait)

    def _config_wait_for(ap):
        ap.add_argument("selector")
        ap.add_argument("--timeout-ms", type=int, default=10000)
        ap.add_argument("--state", default="visible",
                        choices=["attached", "detached", "visible", "hidden"])
        ap.set_defaults(func=cmd_wait_for)

    def _config_hover(ap):
        ap.add_argument("--selector", default=None)
        ap.add_argument("--x", type=int, default=None)
        ap.add_argument("--y", type=int, default=None)
        ap.set_defaults(func=cmd_hover)

    def _config_select(ap):
        ap.add_argument("selector")
        ap.add_argument("value", help="option value (or comma-separated for multi)")
        ap.set_defaults(func=cmd_select)

    def _config_viewport(ap):
        ap.add_argument("width", type=int)
        ap.add_argument("height", type=int)
        ap.set_defaults(func=cmd_viewport)

    def _config_eval(ap):
        ap.add_argument("js", help="JavaScript expression or function body")
        ap.set_defaults(func=cmd_eval)

    def _config_get_elements(ap):
        ap.add_argument("selector")
        ap.add_argument("--limit", type=int, default=50)
        ap.set_defaults(func=cmd_get_elements)

    def _config_back(ap):
        ap.set_defaults(func=cmd_back)

    def _config_forward(ap):
        ap.set_defaults(func=cmd_forward)

    _add_action("click", "click at viewport coordinates", _config_click)
    _add_action("click-selector", "click an element matching a CSS selector", _config_click_selector)
    _add_action("type", "type text (into focused element or a selector)", _config_type)
    _add_action("key", "press a named key (Enter, Tab, Escape, ...)", _config_key)
    _add_action("scroll", "scroll the page in a direction", _config_scroll)
    _add_action("wait", "wait N milliseconds", _config_wait)
    _add_action("wait-for", "wait for a selector to reach a state", _config_wait_for)
    _add_action("hover", "hover over a selector or coordinates", _config_hover)
    _add_action("select", "select an option in a <select> dropdown", _config_select)
    _add_action("viewport", "resize the viewport", _config_viewport)
    _add_action("eval", "evaluate arbitrary JavaScript on the page", _config_eval)
    _add_action("get-elements", "list elements matching a selector with bboxes", _config_get_elements)
    _add_action("back", "go back one step in history", _config_back)
    _add_action("forward", "go forward one step in history", _config_forward)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    try:
        func(args)
        return 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
