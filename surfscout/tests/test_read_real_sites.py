"""Real-site network tests. Opt-in via `pytest -m network`.

Asserts shape (markdown non-empty, contains expected anchors), not exact content.
Tolerates flake — these tests hit live sites and depend on Akamai/PerimeterX
mood, listing availability, etc.

Day 2 status (2026-05-01):
- LandWatch: works fully (price + acres + description via facts pre-extraction)
- Redfin: works (price extraction reliable; structured fields render)
- Zillow / Land.com / Realtor.com: blocked by tier-1 WAF (PerimeterX, strict
  Akamai). Needs warmed persistent profile — Day 4 work.

Run with: pytest tests/test_read_real_sites.py -m network -v
Skip by default: regular `pytest` runs do not invoke network tests.
"""

from __future__ import annotations

import pytest

from surfscout.read import read_url

pytestmark = pytest.mark.network


# ────────────────────────────────────────────────────────────────────────────
# LandWatch — primary target for Venus's homestead landsearch
# ────────────────────────────────────────────────────────────────────────────


def test_landwatch_individual_listing_extracts_price_and_acres():
    """Individual LandWatch listing should yield price + acres + description."""
    url = (
        "https://www.landwatch.com/saguache-county-colorado-farms-and-ranches"
        "-for-sale/pid/425988405"
    )
    result = read_url(url)

    assert result["title"], "title should be populated"
    assert "LandWatch" in result["title"] or "Colorado" in result["title"]
    assert result["facts"]["price"] is not None, "price should be extracted"
    assert result["facts"]["acres"] is not None, "acres should be extracted"
    assert result["facts"]["price"].startswith("$"), "price should be dollar-formatted"
    assert "**Price:**" in result["markdown"], "facts block should be in markdown"
    assert "**Acres:**" in result["markdown"], "facts block should be in markdown"
    assert result["char_count"] > 500, "should have meaningful body content"


def test_landwatch_search_results_renders():
    """LandWatch filtered search results page should render past Akamai."""
    url = (
        "https://www.landwatch.com/colorado-land-for-sale/acres-50-100"
        "/price-under-200000"
    )
    result = read_url(url)

    assert "Access Denied" not in result["title"], "should pass Akamai"
    assert "Colorado" in result["title"]
    assert result["char_count"] > 500


def test_landwatch_search_results_no_readability_yields_all_cards():
    """--no-readability mode preserves the card grid on search-results pages.

    Before this mode existed, Readability stripped down to ~2 listing URLs.
    With --no-readability the full body is markdownified, yielding all
    page-1 listings (LandWatch paginates at 25/page).
    """
    import re

    url = (
        "https://www.landwatch.com/colorado-land-for-sale/acres-50-100"
        "/price-under-200000"
    )
    result = read_url(url, use_readability=False)

    assert result["extraction_method"] == "markdownify_only"
    assert "Access Denied" not in result["title"]

    pids = sorted(set(re.findall(r"/pid/(\d+)", result["markdown"])))
    # Should yield substantially more than the 2 Readability used to leak
    assert len(pids) >= 10, (
        f"expected >=10 listing pids, got {len(pids)} — "
        f"--no-readability should preserve the card grid"
    )


# ────────────────────────────────────────────────────────────────────────────
# Redfin — secondary source
# ────────────────────────────────────────────────────────────────────────────


def test_redfin_listing_extracts_price():
    """Redfin listing should at minimum yield a price.

    Note: Redfin redirects unknown URLs to nearby comparable listings, so we
    don't assert specific addresses — only that the extraction pipeline
    produces a usable result.
    """
    url = "https://www.redfin.com/CO/Westcliffe/Schoolfield-Rd-81252/home/171891011"
    result = read_url(url)

    assert "denied" not in result["title"].lower(), "should pass Redfin's bot check"
    assert result["facts"]["price"] is not None, "price should be extracted"
    assert result["char_count"] > 500


# ────────────────────────────────────────────────────────────────────────────
# Sites blocked at Day 2 — kept as xfail so future work has a hook
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="PerimeterX 'Press & Hold' challenge; needs warmed profile (Day 4)",
    strict=False,
)
def test_zillow_listing_renders():
    url = "https://www.zillow.com/homedetails/2024-S-Cherokee-St-Denver-CO-80223/13345095_zpid/"
    result = read_url(url)
    assert "denied" not in result["title"].lower()


@pytest.mark.xfail(
    reason="Akamai tier-1 block; needs warmed profile (Day 4)",
    strict=False,
)
def test_land_com_renders():
    url = "https://www.land.com/Colorado/all-land/"
    result = read_url(url)
    assert "Access Denied" not in result["title"]


@pytest.mark.xfail(
    reason="WAF block; needs warmed profile (Day 4)",
    strict=False,
)
def test_realtor_com_renders():
    url = (
        "https://www.realtor.com/realestateandhomes-search/Colorado/type-land"
        "/price-na-200000"
    )
    result = read_url(url)
    assert result["char_count"] > 500
