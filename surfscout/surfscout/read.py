"""Tool 1 — `surfscout read <url>`. Render → extract → markdown.

Standalone (no daemon dependency). Spawns its own ephemeral browser per call.

Pipeline:
1. Playwright + stealth renders the page
2. Wait for content to settle (domcontentloaded + settle delay + body-text probe)
3. Pre-extract high-signal facts (price, acres) from body innerText
4. Try Readability.js (vendored) for main-content extraction
5. Fall back to readability-lxml (Python) if JS path returns null/empty
6. Final fallback: markdownify the cleaned body
7. Prepend facts block so Venus always sees price+acreage even when
   Readability strips them as out-of-boundary chrome

Output target: clean markdown, ideally <10K tokens per page.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from surfscout.stealth import apply_stealth

# Paths
VENDOR_DIR = Path(__file__).parent / "vendor"
READABILITY_JS_PATH = VENDOR_DIR / "Readability.js"

# Tunables
DEFAULT_SETTLE_MS = 1500          # wait this long after domcontentloaded
DEFAULT_TIMEOUT_MS = 30_000        # overall navigation timeout
MIN_BODY_TEXT_LEN = 200            # if body text shorter, retry with longer wait
RETRY_SETTLE_MS = 5000             # extended settle on retry
VIEWPORT = {"width": 1280, "height": 800}

# Realistic context dressing — defeats most header/locale-based WAF heuristics.
# UA matches the bundled Nix chromium (141.x) so it stays internally consistent
# with navigator.userAgentData when stealth applies its patches.
REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
REALISTIC_LOCALE = "en-US"
REALISTIC_TIMEZONE = "America/New_York"
REALISTIC_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Markdownify config: heading style ATX, dash bullets, strip nav/script/style
MARKDOWNIFY_KWARGS = {
    "heading_style": "ATX",
    "bullets": "-",
    "strip": ["script", "style", "nav", "footer", "aside", "form", "noscript"],
    "escape_asterisks": False,
    "escape_underscores": False,
}


# Fact-extraction regexes — used to surface high-signal numbers that Readability
# tends to strip when they live in sidebars/headers outside the article boundary.
# Real estate listings put price + acreage in chrome elements, not body prose.
_PRICE_RE = re.compile(r"\$[\d,]{3,}(?:\.\d{2})?")
_ACRES_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*[Aa]cres?\b")


def _extract_facts(body_text: str) -> dict[str, str | None]:
    """Pull first price + first acreage from raw body text.

    Best-effort: returns the first match of each pattern. On listing detail pages
    the primary listing's price/acreage almost always appears first in DOM order
    (above the fold, before similar-listings sidebars). Search-results pages will
    return the first card's numbers — still better than nothing.
    """
    price_match = _PRICE_RE.search(body_text)
    acres_match = _ACRES_RE.search(body_text)
    return {
        "price": price_match.group(0) if price_match else None,
        "acres": acres_match.group(0) if acres_match else None,
    }


def _format_facts_block(facts: dict[str, str | None]) -> str:
    """Render a facts dict as a markdown frontmatter-style block, or empty string."""
    lines = []
    if facts.get("price"):
        lines.append(f"**Price:** {facts['price']}")
    if facts.get("acres"):
        lines.append(f"**Acres:** {facts['acres']}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n\n"


def _load_readability_js() -> str | None:
    """Load vendored Readability.js, or return None if not vendored yet."""
    if READABILITY_JS_PATH.exists():
        return READABILITY_JS_PATH.read_text(encoding="utf-8")
    return None


async def _extract_via_readability_js(page, readability_src: str) -> dict[str, Any] | None:
    """Inject Readability.js, run it on the document, return parsed result.

    Returns a dict with keys like {title, content, textContent, length, excerpt}
    or None if extraction failed.
    """
    try:
        await page.add_script_tag(content=readability_src)
        result = await page.evaluate(
            """() => {
                try {
                    const doc = document.cloneNode(true);
                    const reader = new Readability(doc);
                    return reader.parse();
                } catch (e) {
                    return null;
                }
            }"""
        )
        return result
    except Exception:
        return None


def _extract_via_readability_lxml(html: str) -> str | None:
    """Python fallback: use readability-lxml to extract main content HTML."""
    try:
        from readability import Document
    except ImportError:
        return None
    try:
        doc = Document(html)
        return doc.summary(html_partial=False)
    except Exception:
        return None


def _html_to_markdown(html: str) -> str:
    """Convert HTML to markdown via markdownify."""
    from markdownify import markdownify as md

    text = md(html, **MARKDOWNIFY_KWARGS)
    # Collapse runs of 3+ blank lines to 2
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_streak = 0
    for line in lines:
        if line.strip():
            cleaned.append(line)
            blank_streak = 0
        else:
            blank_streak += 1
            if blank_streak <= 2:
                cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


async def extract_from_page(
    page,
    settle_ms: int = DEFAULT_SETTLE_MS,
    use_readability: bool = True,
) -> dict[str, Any]:
    """Run the full extraction pipeline against an already-navigated page.

    Reusable across Tool 1 (ephemeral) and the daemon `read` handler
    (warmed persistent context). Caller is responsible for navigating the
    page to the target URL before calling this.

    Args:
        page: Playwright page, already navigated.
        settle_ms: Wait this long after navigation before extraction.
        use_readability: If True (default), run Readability.js + lxml fallback
            for main-content extraction. If False, skip Readability entirely
            and markdownify the full body — preserves card grids on
            search-results pages where Readability over-strips.

    Returns the same dict shape as read_url_async.
    """
    readability_src = _load_readability_js() if use_readability else None

    await page.wait_for_timeout(settle_ms)

    # Probe body text length; retry with longer settle if too short
    body_len = await page.evaluate("document.body.innerText.length")
    if body_len < MIN_BODY_TEXT_LEN:
        await page.wait_for_timeout(RETRY_SETTLE_MS)

    # Pre-extract high-signal facts before Readability strips them
    body_text = await page.evaluate("document.body.innerText")
    facts = _extract_facts(body_text)

    final_url = page.url
    title = await page.title()

    # Path 1: Readability.js (skipped when use_readability=False)
    extraction_method = "markdownify_only"
    content_html: str | None = None

    if readability_src:
        parsed = await _extract_via_readability_js(page, readability_src)
        if parsed and parsed.get("content"):
            content_html = parsed["content"]
            if not title and parsed.get("title"):
                title = parsed["title"]
            extraction_method = "readability_js"

    # Path 2: readability-lxml fallback (also skipped when use_readability=False)
    if not content_html and use_readability:
        full_html = await page.content()
        content_html = _extract_via_readability_lxml(full_html)
        if content_html:
            extraction_method = "readability_lxml"

    # Path 3: just take the body innerHTML
    if not content_html:
        content_html = await page.evaluate("document.body.innerHTML")

    markdown = _html_to_markdown(content_html or "")
    facts_block = _format_facts_block(facts)
    markdown = facts_block + markdown

    return {
        "url": final_url,
        "title": title,
        "markdown": markdown,
        "extraction_method": extraction_method,
        "char_count": len(markdown),
        "facts": facts,
    }


async def read_url_async(
    url: str,
    settle_ms: int = DEFAULT_SETTLE_MS,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    headless: bool = True,
    use_readability: bool = True,
) -> dict[str, Any]:
    """Render URL in an ephemeral browser, extract main content, return markdown.

    Tool 1 entry point. Stateless — no shared state with the daemon's
    persistent profile.

    For warmed-profile reads (logged-in sites, WAF-protected sites where the
    daemon has already passed the bot challenge in headed mode), use the
    daemon `read` handler instead via `surfscout read --use-daemon`.

    Set use_readability=False for search-results / card-grid pages where
    Readability over-strips and you want the full body markdown instead.

    Returns dict: {url, title, markdown, extraction_method, char_count, facts}
    """
    # Honor SURFSCOUT_CHROMIUM_PATH — set by the bin/surfscout shim on NixOS
    # to point at a Nix-managed playwright-chromium (rpath-linked). On other
    # distros this is unset and Playwright uses its bundled browser.
    import os
    chromium_path = os.environ.get("SURFSCOUT_CHROMIUM_PATH") or None

    async with async_playwright() as pw:
        launch_kwargs: dict[str, Any] = {"headless": headless}
        if chromium_path:
            launch_kwargs["executable_path"] = chromium_path
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport=VIEWPORT,
            user_agent=REALISTIC_USER_AGENT,
            locale=REALISTIC_LOCALE,
            timezone_id=REALISTIC_TIMEZONE,
            extra_http_headers=REALISTIC_HEADERS,
        )
        await apply_stealth(context)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return await extract_from_page(
                page, settle_ms=settle_ms, use_readability=use_readability
            )
        finally:
            await context.close()
            await browser.close()


def read_url(url: str, **kwargs) -> dict[str, Any]:
    """Synchronous wrapper around read_url_async."""
    return asyncio.run(read_url_async(url, **kwargs))
