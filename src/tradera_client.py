"""
Client for Tradera's OFFICIAL SOAP v3 API.

Setup required before this works:
1. Register at https://api.tradera.com/ (Tradera Developer Program)
2. Accept the Terms of Use + Logo Terms of Use
3. You'll receive an App ID (numeric, e.g. 6393) and an App Key (a GUID secret)
4. Put them in your .env file as TRADERA_APP_ID / TRADERA_APP_KEY (see .env.example)

This module has been validated live against Tradera's current WSDL:
  - Search       -> searchservice.asmx  (SearchAdvanced / Search)
  - GetCategories -> publicservice.asmx  (categories live on the PUBLIC service)
Both services require BOTH an AuthenticationHeader and a ConfigurationHeader.

If field names ever drift, run `python -m src.tradera_client` (see bottom of
file) to sanity-check the call, and inspect the schema at
https://api.tradera.com/v3/searchservice.asmx?WSDL
"""
from __future__ import annotations

import os
from typing import Any

from zeep import Client
from zeep.helpers import serialize_object

SEARCH_WSDL = "https://api.tradera.com/v3/searchservice.asmx?WSDL"
PUBLIC_WSDL = "https://api.tradera.com/v3/publicservice.asmx?WSDL"

# Tradera's PriceMaximum filter is an absolute cap: sending 0 means
# "max price 0 SEK", which matches nothing. When the caller wants no upper
# bound we send this sentinel instead (well within xsd:int / int32 range).
_NO_PRICE_MAX = 2_000_000_000

_search_client: Client | None = None
_public_client: Client | None = None


def _get_credentials() -> tuple[int, str]:
    app_id = os.environ.get("TRADERA_APP_ID")
    app_key = os.environ.get("TRADERA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError(
            "Missing TRADERA_APP_ID / TRADERA_APP_KEY environment variables. "
            "Register at https://api.tradera.com/ and set them in your .env "
            "or Claude Desktop MCP config."
        )
    try:
        app_id_int = int(app_id)
    except ValueError as exc:
        raise RuntimeError(
            f"TRADERA_APP_ID must be a numeric App ID (e.g. 6393), got {app_id!r}."
        ) from exc
    return app_id_int, app_key


def _search_soap_client() -> Client:
    global _search_client
    if _search_client is None:
        _search_client = Client(SEARCH_WSDL)
    return _search_client


def _public_soap_client() -> Client:
    global _public_client
    if _public_client is None:
        _public_client = Client(PUBLIC_WSDL)
    return _public_client


def _headers(client: Client) -> list[Any]:
    """Both Tradera services require an Authentication AND a Configuration header."""
    app_id, app_key = _get_credentials()
    auth_type = client.get_element("ns0:AuthenticationHeader")
    conf_type = client.get_element("ns0:ConfigurationHeader")
    auth = auth_type(AppId=app_id, AppKey=app_key)
    conf = conf_type(Sandbox=0, MaxResultAge=0)
    return [auth, conf]


def _first_image_url(image_links: Any) -> str | None:
    """Pull a usable image URL out of the ImageLinks/ArrayOfImageLink structure."""
    if not isinstance(image_links, dict):
        return None
    links = image_links.get("ImageLink") or []
    if isinstance(links, dict):
        links = [links]
    if not links:
        return None
    # Prefer a normal-sized image, else fall back to the first one.
    for link in links:
        if isinstance(link, dict) and link.get("Format") == "normal":
            return link.get("Url")
    first = links[0]
    return first.get("Url") if isinstance(first, dict) else None


def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Tradera SearchItem into the common shape shared with Blocket."""
    item_id = raw.get("Id") or raw.get("ItemId")
    return {
        "source": "tradera",
        "id": item_id,
        "title": raw.get("ShortDescription") or raw.get("LongDescription"),
        # Buy-It-Now if present, otherwise the current/next bid for auctions.
        "price_sek": raw.get("BuyItNowPrice") or raw.get("MaxBid") or raw.get("NextBid"),
        "item_type": raw.get("ItemType"),  # "Auction", "BuyItNow", etc.
        "bid_count": raw.get("BidCount"),
        "location": None,  # Tradera search results don't include seller location
        "url": raw.get("ItemUrl") or (f"https://www.tradera.com/item/{item_id}" if item_id else None),
        "image_url": raw.get("ThumbnailLink") or _first_image_url(raw.get("ImageLinks")),
        "ends_at": str(raw.get("EndDate")) if raw.get("EndDate") else None,
        "is_ended": raw.get("IsEnded"),
        "seller_alias": raw.get("SellerAlias"),
        "_raw": raw,
    }


async def search_tradera(
    query: str,
    category_id: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """
    Search Tradera listings via the official SearchService (SearchAdvanced).

    Args:
        query: Free-text search query.
        category_id: Optional Tradera category ID (call get_categories() to list them).
        price_min / price_max: Optional SEK price bounds.
        max_results: Cap on number of results (Tradera returns up to 50 per page).

    Returns:
        dict with "items": list of normalized listings, or "error" if the call failed.
    """
    try:
        client = _search_soap_client()
        request_type = client.get_type("ns0:SearchAdvancedRequest")
        request = request_type(
            SearchWords=query,
            CategoryId=category_id or 0,
            SearchInDescription=False,
            PriceMinimum=price_min or 0,
            # 0 would mean "max price 0 SEK" (no matches); use a sentinel instead.
            PriceMaximum=price_max if price_max else _NO_PRICE_MAX,
            BidsMinimum=0,
            BidsMaximum=0,
            CountyId=0,
            OnlyAuctionsWithBuyNow=False,
            OnlyItemsWithThumbnail=False,
            ItemsPerPage=max(1, min(max_results, 50)),
            PageNumber=1,
        )

        result = client.service.SearchAdvanced(
            request=request,
            _soapheaders=_headers(client),
        )
        result = serialize_object(result)

        items = (result or {}).get("Items") or []
        if isinstance(items, dict):  # single-result edge case
            items = [items]

        normalized = [_normalize_item(i) for i in items[:max_results]]
        return {
            "items": normalized,
            "count": len(normalized),
            "total_available": (result or {}).get("TotalNumberOfItems"),
        }

    except Exception as e:  # noqa: BLE001 — surface the raw error to the agent, it's actionable
        return {
            "error": str(e),
            "hint": (
                "Check TRADERA_APP_ID/TRADERA_APP_KEY are set and valid, and that "
                "the SearchAdvanced request fields above still match Tradera's "
                "current WSDL — SOAP APIs occasionally rename fields. Fetch "
                f"{SEARCH_WSDL} directly in a browser to inspect the current schema."
            ),
        }


async def get_categories() -> dict[str, Any]:
    """Fetch Tradera's category tree, useful for finding category_id values.

    NOTE: GetCategories lives on the PUBLIC service, not the search service.
    """
    try:
        client = _public_soap_client()
        result = client.service.GetCategories(_soapheaders=_headers(client))
        return {"categories": serialize_object(result)}
    except Exception as e:  # noqa: BLE001
        return {
            "error": str(e),
            "hint": (
                "Check TRADERA_APP_ID/TRADERA_APP_KEY are set and valid. "
                f"GetCategories is served by {PUBLIC_WSDL}."
            ),
        }


if __name__ == "__main__":
    # Quick manual sanity check — run with TRADERA_APP_ID/KEY set:
    #   python -m src.tradera_client
    import asyncio
    import json

    from dotenv import load_dotenv

    load_dotenv()

    async def _main() -> None:
        res = await search_tradera("iphone", max_results=5)
        print(json.dumps(res, indent=2, default=str))

    asyncio.run(_main())
