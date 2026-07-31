"""
Facebook Marketplace search — UNOFFICIAL, HIGHER RISK than the other two.

There is no public API for Facebook Marketplace. The only known approaches:
  1. Replay Facebook's internal GraphQL requests using your logged-in
     session cookies (see github.com/jdcodes1/facebook-marketplace-mcp).
  2. Headless-browser scraping (see github.com/jlsookiki/secondhand-mcp).

Both technically violate Facebook's Terms of Service, which explicitly
prohibit automated data collection. Risk is account suspension at minimum.
This is why it's OFF by default here (ENABLE_FACEBOOK_SEARCH must be set).

This module is intentionally left as a stub rather than a working scraper:
plugging in either of the approaches above requires cookie/session
extraction specific to your OS and browser, and both are liable to break
whenever Facebook changes its internal API. If you decide to proceed:
  - Read github.com/jdcodes1/facebook-marketplace-mcp for the GraphQL
    doc_id + cookie approach (macOS/Chrome only, uses Keychain)
  - Or github.com/jlsookiki/secondhand-mcp for a Playwright-based approach
  - Adapt whichever fits your OS into `search_facebook()` below
  - Keep using it for PERSONAL browsing only, not for a monetized product
"""
from __future__ import annotations

import os
from typing import Any


def facebook_search_enabled() -> bool:
    return os.environ.get("ENABLE_FACEBOOK_SEARCH", "").lower() in ("1", "true", "yes")


async def search_facebook(
    query: str,
    location: str | None = None,
    radius_km: int = 40,
) -> dict[str, Any]:
    """
    Search Facebook Marketplace. DISABLED BY DEFAULT — see module docstring.

    Set ENABLE_FACEBOOK_SEARCH=1 in your environment only after you've
    implemented one of the approaches referenced above and accepted the
    ToS/account risk described there.
    """
    if not facebook_search_enabled():
        return {
            "error": "facebook_search_disabled",
            "message": (
                "Facebook Marketplace search is disabled by default because it "
                "requires an unofficial method (session cookies or scraping) "
                "that violates Facebook's Terms of Service. See the docstring "
                "in src/facebook_client.py for how to enable it if you accept "
                "that risk for personal use."
            ),
        }

    # Placeholder — not implemented. Replace with your chosen approach.
    return {
        "error": "not_implemented",
        "message": "search_facebook() is a stub. Implement it per the module docstring.",
    }
