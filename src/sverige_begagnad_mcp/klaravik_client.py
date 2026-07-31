"""
Client for Klaravik (klaravik.se) — a Swedish online auction house.

UNOFFICIAL: Klaravik publishes no public API. This calls the same internal
JSON endpoint the website uses (`/api/products/list/search`), which returns
live auction listings with the current bid. Great for undervalued tools,
machinery, and house-clearance goods. It may change or start requiring
bot-protection tokens at any time.

Prices are the CURRENT BID in SEK (auctions), so they can rise before the
auction ends — treat them as a floor, not a final price.
"""
from __future__ import annotations

from typing import Any

import httpx

SEARCH_URL = "https://www.klaravik.se/api/products/list/search"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
_TIMEOUT = httpx.Timeout(30.0)


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    item_id = raw.get("id")
    main_image = raw.get("mainImage") or {}
    image_url = main_image.get("imageUrlThumb") if isinstance(main_image, dict) else None

    parts = [raw.get("municipalityName"), raw.get("countyName")]
    location = ", ".join(p for p in parts if p) or None

    categories = [raw.get("categoryNameLevel1"), raw.get("categoryNameLevel2"), raw.get("categoryNameLevel3")]
    category = " / ".join(c for c in categories if c) or None

    return {
        "source": "klaravik",
        "id": item_id,
        "title": raw.get("name"),
        "make": raw.get("make"),
        "model": raw.get("model"),
        # Auction: current bid is the live price; starting price for reference.
        "price_sek": raw.get("currentBid"),
        "starting_price_sek": raw.get("startingPrice"),
        "num_bids": raw.get("amountOfBids"),
        "category": category,
        "location": location,
        "url": raw.get("url"),
        "image_url": image_url,
        "ends_at": raw.get("endDate"),
        "is_ended": raw.get("ended"),
        "_raw": raw,
    }


async def search_klaravik(query: str, max_results: int = 50) -> dict[str, Any]:
    """
    Search Klaravik auctions for `query` (Swedish terms work best).

    Returns dict with "items": list of normalized listings, or "error".
    """
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    all_items: list[dict[str, Any]] = []
    total: int | None = None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
            page = 1
            while len(all_items) < max_results:
                resp = await client.get(SEARCH_URL, params={"text": query, "page": page})
                resp.raise_for_status()
                data = (resp.json() or {}).get("data") or {}
                items = data.get("items") or []
                if total is None:
                    total = (data.get("pagination") or {}).get("totalCount")
                if not items:
                    break
                all_items.extend(items)
                pagination = data.get("pagination") or {}
                if page >= (pagination.get("totalPages") or 1):
                    break
                page += 1

        normalized = [_normalize(i) for i in all_items[:max_results]]
        return {"items": normalized, "count": len(normalized), "total_available": total}

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "hint": "Klaravik may have changed its internal API or added bot protection.",
        }
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


if __name__ == "__main__":
    import asyncio
    import json

    async def _main() -> None:
        print(json.dumps(await search_klaravik("bahco", max_results=5), indent=2, ensure_ascii=False, default=str))

    asyncio.run(_main())
