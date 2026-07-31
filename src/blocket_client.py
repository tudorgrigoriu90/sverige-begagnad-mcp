"""
Wrapper around the community `blocket-api` PyPI package.

This is an UNOFFICIAL client — Blocket does not publish a public API.
The underlying package replays requests to api.blocket.se using a token
observed in normal browser traffic. It has been stable for the maintainer,
but Blocket could change auth behavior at any time without notice.

If this stops working, check https://pypi.org/project/blocket-api/ for
a newer version, or https://github.com/dunderrrrrr/blocket_api for issues.
"""
from __future__ import annotations

from typing import Any

from blocket_api import AsyncBlocketAPI, Category, Location, SortOrder

# Only the counties relevant to a Växjö / Älmhult radius.
# Blocket's location filter is REGIONAL (län), not a precise radius —
# there is no lat/lng radius filter available in the unofficial API.
# Kronoberg covers Växjö + Älmhult. We also include the bordering counties
# so nothing just across a county line is missed; the LLM should still
# apply the real 30-min-drive filter itself using each ad's stated location.
RELEVANT_LOCATIONS = [
    Location.KRONOBERG,      # Växjö, Älmhult
    Location.KALMAR,         # bordering county, east
    Location.JONKOPING,      # bordering county, north
    Location.HALLAND,        # bordering county, west
    Location.SKANE,          # bordering county, south
]

CATEGORY_MAP = {c.name.lower(): c for c in Category}


def list_categories() -> list[str]:
    """Return all Blocket category names this client can filter on."""
    return sorted(CATEGORY_MAP.keys())


def _normalize_ad(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a raw Blocket search "doc" into the common shape shared with
    Tradera. Field names below match api.blocket.se's current recommerce
    search response; older/alternate keys are kept as fallbacks so nothing
    is silently lost if the shape drifts. The raw payload is always attached.
    """
    price = raw.get("price")
    if isinstance(price, dict):
        # Current API uses "amount"; keep "value" as a legacy fallback.
        price_value = price.get("amount") if price.get("amount") is not None else price.get("value")
    else:
        price_value = price

    location = raw.get("location")
    if isinstance(location, list) and location:
        location_name = location[0].get("name") if isinstance(location[0], dict) else str(location[0])
    elif isinstance(location, dict):
        location_name = location.get("name")
    else:
        location_name = location

    # Image can arrive as a dict ({"url": ...}), a list of such dicts, a bare
    # list of URL strings, or a separate "image_urls" list.
    image_url = None
    image = raw.get("image")
    if isinstance(image, dict):
        image_url = image.get("url")
    elif isinstance(image, list) and image:
        image_url = image[0].get("url") if isinstance(image[0], dict) else image[0]
    elif isinstance(image, str):
        image_url = image
    if image_url is None:
        image_urls = raw.get("image_urls")
        if isinstance(image_urls, list) and image_urls:
            image_url = image_urls[0]

    ad_id = raw.get("ad_id") or raw.get("id") or raw.get("list_id")

    coordinates = raw.get("coordinates") if isinstance(raw.get("coordinates"), dict) else None

    return {
        "source": "blocket",
        "id": ad_id,
        "title": raw.get("heading") or raw.get("subject") or raw.get("title"),
        "price_sek": price_value,
        "location": location_name,
        # Exact lat/lon + Blocket's own distance help the LLM apply the real
        # "30 min drive from Växjö" filter that the regional filter can't.
        "coordinates": coordinates,
        "distance": raw.get("distance"),
        "url": raw.get("canonical_url") or raw.get("share_url") or raw.get("url")
        or (f"https://www.blocket.se/annons/_/{ad_id}" if ad_id else None),
        "image_url": image_url,
        "listed_at": raw.get("timestamp") or raw.get("list_time") or raw.get("published"),
        "description_snippet": (raw.get("body") or raw.get("description") or "")[:280],
        "_raw": raw,
    }


async def search_blocket(
    query: str,
    category: str | None = None,
    locations: list[str] | None = None,
    max_pages: int = 2,
) -> dict[str, Any]:
    """
    Search Blocket for listings matching `query`.

    Args:
        query: Free-text search query (Swedish terms work best, e.g. "String hylla").
        category: Optional category name from list_categories(), e.g. "mobler_och_inredning".
        locations: Optional list of Location enum names (e.g. ["KRONOBERG"]).
                   Defaults to Kronoberg + bordering counties if not given.
        max_pages: How many result pages to fetch (each page ~60 ads). Keep small to limit load.

    Returns:
        dict with "ads": list of normalized ad dicts, and "warning" if category was invalid.
    """
    warning = None
    cat = None
    if category:
        cat = CATEGORY_MAP.get(category.lower())
        if cat is None:
            warning = f"Unknown category '{category}'. Ignoring filter. Valid options: {list_categories()}"

    locs = RELEVANT_LOCATIONS
    if locations:
        locs = [Location[loc.upper()] for loc in locations if loc.upper() in Location.__members__]

    api = AsyncBlocketAPI()
    all_ads: list[dict[str, Any]] = []
    try:
        for page in range(1, max_pages + 1):
            result = await api.search(
                query,
                page=page,
                sort_order=SortOrder.RELEVANCE,
                locations=locs,
                category=cat,
            )
            # The recommerce search endpoint returns results under "docs";
            # older/alternate keys kept as fallbacks.
            ads = result.get("docs") or result.get("data") or result.get("ads") or []
            if not ads:
                break
            all_ads.extend(_normalize_ad(a) for a in ads)
    finally:
        await api.aclose()

    out: dict[str, Any] = {"ads": all_ads, "count": len(all_ads)}
    if warning:
        out["warning"] = warning
    return out
