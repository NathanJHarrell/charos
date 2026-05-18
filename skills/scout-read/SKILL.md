---
name: scout-read
description: Render a web URL through SurfScout (real Chromium with stealth + Readability) and return clean markdown. Use when fetching a single URL for content — listing details, article text, search-results page, anything that returns 403 to plain HTTP requests. Standalone, no daemon needed. For multi-step browser interaction (clicks, forms, pagination), use scout-do instead.
---

# scout-read

SurfScout's Tool 1. Renders a URL in a real ephemeral Chromium with playwright-stealth and realistic context dressing (UA, locale, timezone, headers), extracts main content via vendored Mozilla Readability.js, returns clean markdown.

Default behavior beats most WAF/bot-detection that rejects plain HTTP. Verified working on LandWatch, Redfin, Amazon Prime Video. Blocked on Zillow / Land.com / Realtor.com without warmed profile (use `scout-do` + `--use-daemon` for those).

## When to use

- Pulling content from a single URL where plain `curl` returns 403
- Extracting an article, listing detail, blog post, or product page
- One-shot reads that don't need cookies, login, or interaction
- Search-results pages (use `--no-readability` to preserve card grids)

**Don't use for:** form-filling, multi-page navigation, anything that needs cookies / login state. Use `scout-do` instead.

## How to use

Run via Bash:

```bash
# Default — clean markdown to stdout
surfscout read "https://www.example.com/article"

# JSON output with metadata + facts (price/acres for listings)
surfscout read "https://www.landwatch.com/saguache-county-colorado-farms-and-ranches-for-sale/pid/425988405" --json

# Search-results / card-grid pages — skip Readability so all cards survive
surfscout read "https://www.landwatch.com/colorado-land-for-sale/acres-50-100/price-under-200000" --no-readability

# Slow-loading SPA — wait longer for JS to settle, bump the overall timeout
surfscout read "https://some-slow-spa.example/path" --settle-ms 5000 --timeout-ms 60000
```

### Flag reference

- `--settle-ms <ms>` — extra time (after `load`) to wait for client-side rendering before extraction. Default 1500. Bump to 3000–5000 for JS-heavy SPAs whose content paints late.
- `--timeout-ms <ms>` — overall navigation/render timeout. Default 30000. Bump when the target is slow or you're on flaky network.

## Output shape

- Default: markdown to stdout
- `--json`: `{url, title, markdown, extraction_method, char_count, facts: {price, acres}}`

`extraction_method` is `readability_js` | `readability_lxml` | `markdownify_only`. The first two are clean-article extraction; `markdownify_only` is full-body (used when `--no-readability` is passed or when both extractors return empty).

`facts` is a best-effort price + acres pull from raw body text — works on real estate listings. `null` for both if neither pattern matches.

## Failure modes

- WAF block: `title` will be "Access Denied" or markdown will be ~200 chars of challenge text. Switch to `scout-do` + warmed profile.
- Empty markdown: site rendered nothing (JS-only SPA with slow load). Try `--settle-ms 5000`.
- Timeout: bump `--timeout-ms` (default 30000).

## Related

- `scout-do` — full Tool 2 surface for interactive sessions
- Project: `~/charos/surfscout/`
- Primer: `~/charos/surfscout/PRIMER.md`
