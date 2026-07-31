"""
Client for Vinted (vinted.se) — a large pan-European second-hand fashion
marketplace, active in Sweden. Good for genuine leather/wool and branded
clothing.

UNOFFICIAL: Vinted has no public API. This calls the same internal endpoint
the website uses (`/api/v2/catalog/items`). Vinted is behind bot protection
(DataDome), so this first loads the homepage to obtain session cookies, then
calls the API with the headers the site sends. It can still be rate-limited
or blocked, especially from datacenter IPs — running locally (residential IP)
works best. This is the most fragile of the sources.

Set VINTED_DOMAIN to use another country domain (default "vinted.se").
"""
from __future__ import annotations

import os
from typing import Any

import httpx

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
_TIMEOUT = httpx.Timeout(30.0)


def _domain() -> str:
    return os.environ.get("VINTED_DOMAIN", "vinted.se")


def _to_int_sek(price: Any) -> int | None:
    if isinstance(price, dict):
        price = price.get("amount")
    try:
        return round(float(price))
    except (TypeError, ValueError):
        return None


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    photo = raw.get("photo") or {}
    image_url = None
    if isinstance(photo, dict):
        image_url = photo.get("url") or photo.get("full_size_url")

    return {
        "source": "vinted",
        "id": raw.get("id"),
        "title": raw.get("title"),
        "price_sek": _to_int_sek(raw.get("price")),
        "total_price_sek": _to_int_sek(raw.get("total_item_price")),  # incl. buyer protection fee
        "brand": raw.get("brand_title"),
        "size": raw.get("size_title") or None,
        "status": raw.get("status"),
        "location": None,  # Vinted is national/ship-anywhere
        "url": raw.get("url"),
        "image_url": image_url,
        "_raw": raw,
    }


async def search_vinted(
    query: str,
    price_min: int | None = None,
    price_max: int | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """
    Search Vinted for `query`. Optional SEK price bounds.

    Returns dict with "items": list of normalized listings, or "error".
    """
    domain = _domain()
    base = f"https://www.{domain}"
    headers = {
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{base}/catalog",
        "X-Requested-With": "XMLHttpRequest",
    }
    params: dict[str, Any] = {
        "search_text": query,
        "per_page": max(1, min(max_results, 96)),
        "page": 1,
        "order": "newest_first",
        "currency": "SEK",
    }
    if price_min is not None:
        params["price_from"] = price_min
    if price_max is not None:
        params["price_to"] = price_max

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as client:
            # Warm up: the homepage sets the cookies the API requires.
            await client.get(base)
            resp = await client.get(f"{base}/api/v2/catalog/items", params=params)
            resp.raise_for_status()
            data = resp.json() or {}

        items = data.get("items") or []
        normalized = [_normalize(i) for i in items[:max_results]]
        total = (data.get("pagination") or {}).get("total_entries")
        return {"items": normalized, "count": len(normalized), "total_available": total}

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "hint": (
                "Vinted uses bot protection (DataDome). A 403 usually means the IP is "
                "blocked — it tends to work from a residential connection. Try again, or "
                "set VINTED_DOMAIN to your country."
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


if __name__ == "__main__":
    import asyncio
    import json

    async def _main() -> None:
        print(json.dumps(await search_vinted("iphone", max_results=5), indent=2, ensure_ascii=False, default=str))

    asyncio.run(_main())
