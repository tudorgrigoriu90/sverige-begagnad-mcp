"""
Client for Tradera's OFFICIAL REST API (v4).

Setup required before this works:
1. Register at https://api.tradera.com/register (Tradera Developer Program)
2. Accept the Terms of Use + Logo Terms of Use
3. Create an application to get an App ID (numeric, e.g. 6393) and an App Key (GUID)
4. Put them in your .env file as TRADERA_APP_ID / TRADERA_APP_KEY (see .env.example)

This uses the v4 REST API (https://api.tradera.com/v4), the same API surface
that Tradera's own AI plugin (github.com/tradera/ai-marketplace) is built on.
It supersedes the older SOAP v3 endpoints — auth is a pair of request headers
(X-App-Id / X-App-Key), responses are plain JSON, and no upper-price sentinel
trick is needed (omitting a filter simply means "no bound").

Endpoints used:
  - POST /v4/search/advanced   full-text search with price/category/county filters
  - GET  /v4/categories        category tree
  - GET  /v4/reference-data/counties   county id -> name (for county_id filtering)

Validated live against the current v4 API. If the shape ever drifts, the raw
OpenAPI spec is at https://api.tradera.com/openapi.json
"""
from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = "https://api.tradera.com/v4"
_TIMEOUT = httpx.Timeout(30.0)


def _get_credentials() -> tuple[str, str]:
    app_id = os.environ.get("TRADERA_APP_ID")
    app_key = os.environ.get("TRADERA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError(
            "Missing TRADERA_APP_ID / TRADERA_APP_KEY environment variables. "
            "Register at https://api.tradera.com/register and set them in your "
            ".env or Claude Desktop MCP config."
        )
    return app_id, app_key


def _auth_headers() -> dict[str, str]:
    app_id, app_key = _get_credentials()
    return {"X-App-Id": app_id, "X-App-Key": app_key}


def _first_image_url(image_links: Any) -> str | None:
    """Pick a usable image URL out of the imageLinks array."""
    if not isinstance(image_links, list) or not image_links:
        return None
    for link in image_links:
        if isinstance(link, dict) and link.get("format") == "normal":
            return link.get("url")
    first = image_links[0]
    return first.get("url") if isinstance(first, dict) else None


def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Tradera v4 search item into the common shape shared with Blocket."""
    item_id = raw.get("id")
    return {
        "source": "tradera",
        "id": item_id,
        "title": raw.get("shortDescription") or raw.get("longDescription"),
        # Buy-It-Now if present, otherwise the current/next bid for auctions.
        "price_sek": raw.get("buyItNowPrice") or raw.get("maxBid") or raw.get("nextBid"),
        "item_type": raw.get("itemType"),  # "Auction", "BuyItNow", etc.
        "bid_count": raw.get("bidCount"),
        "location": None,  # Tradera is national/ship-anywhere; no seller location in search
        "url": raw.get("itemUrl") or (f"https://www.tradera.com/item/{item_id}" if item_id else None),
        "image_url": raw.get("thumbnailLink") or _first_image_url(raw.get("imageLinks")),
        "ends_at": raw.get("endDate"),
        "is_ended": raw.get("isEnded"),
        "seller_alias": raw.get("sellerAlias"),
        "_raw": raw,
    }


async def search_tradera(
    query: str,
    category_id: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    county_id: int | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """
    Search Tradera listings via the official v4 REST API (POST /v4/search/advanced).

    Args:
        query: Free-text search query.
        category_id: Optional Tradera category ID (call get_categories() to list them).
        price_min / price_max: Optional SEK price bounds (omit either for no bound).
        county_id: Optional county filter (call get_counties() to list ids). Tradera
                   is national with shipping, so this is rarely needed.
        max_results: Cap on number of results (Tradera returns up to 50 per page).

    Returns:
        dict with "items": list of normalized listings, or "error" if the call failed.
    """
    body: dict[str, Any] = {"searchWords": query, "itemsPerPage": max(1, min(max_results, 50))}
    if category_id:
        body["categoryId"] = category_id
    if price_min is not None:
        body["priceMinimum"] = price_min
    if price_max is not None:
        body["priceMaximum"] = price_max
    if county_id:
        body["countyId"] = county_id

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/search/advanced", headers=_auth_headers(), json=body
            )
            resp.raise_for_status()
            result = resp.json()

        items = (result or {}).get("items") or []
        normalized = [_normalize_item(i) for i in items[:max_results]]
        return {
            "items": normalized,
            "count": len(normalized),
            "total_available": (result or {}).get("totalNumberOfItems"),
        }

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}",
            "hint": (
                "401/403 usually means TRADERA_APP_ID/TRADERA_APP_KEY are missing "
                "or invalid. Register/verify at https://api.tradera.com/register."
            ),
        }
    except Exception as e:  # noqa: BLE001 — surface the raw error to the agent, it's actionable
        return {"error": str(e)}


async def _get_json(path: str) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/{path}", headers=_auth_headers())
        resp.raise_for_status()
        return resp.json()


async def get_categories() -> dict[str, Any]:
    """Fetch Tradera's category tree, useful for finding category_id values."""
    try:
        return {"categories": await _get_json("categories")}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


async def get_counties() -> dict[str, Any]:
    """Fetch Tradera's county list (id -> name) for the optional county_id filter."""
    try:
        return {"counties": await _get_json("reference-data/counties")}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


if __name__ == "__main__":
    # Quick manual sanity check — run with TRADERA_APP_ID/KEY set:
    #   python -m src.tradera_client
    import asyncio
    import json

    from dotenv import load_dotenv

    load_dotenv()

    async def _main() -> None:
        res = await search_tradera("iphone", price_min=100, price_max=500, max_results=5)
        print(json.dumps(res, indent=2, default=str))

    asyncio.run(_main())
