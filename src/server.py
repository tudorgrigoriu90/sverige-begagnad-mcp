"""
Sverige Begagnad MCP — personal-use MCP server for sourcing quality
second-hand items on Blocket, Tradera, and (optionally) Facebook
Marketplace, to flip for profit around Växjö / Älmhult.

Run locally via stdio (see README.md for Claude Desktop config):
    python -m src.server
"""
from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from . import blocket_client, tradera_client, facebook_client  # noqa: E402

mcp = FastMCP("sverige-begagnad")


@mcp.tool(
    title="Search Blocket",
    description=(
        "Search Blocket.se for second-hand listings. Regional location filter only "
        "(no precise radius) — defaults to Kronoberg + bordering counties, covering "
        "Växjö and Älmhult. Use list_blocket_categories() first if you want to filter "
        "by category."
    ),
)
async def search_blocket(
    query: str,
    category: Optional[str] = None,
    max_pages: int = 2,
) -> dict[str, Any]:
    return await blocket_client.search_blocket(query=query, category=category, max_pages=max_pages)


@mcp.tool(
    title="List Blocket categories",
    description="List valid category names to pass into search_blocket()'s `category` argument.",
)
def list_blocket_categories() -> dict[str, Any]:
    return {"categories": blocket_client.list_categories()}


@mcp.tool(
    title="Search Tradera",
    description=(
        "Search Tradera.com (official API) for second-hand listings/auctions. "
        "Requires TRADERA_APP_ID and TRADERA_APP_KEY to be configured — register "
        "at https://api.tradera.com/ if you haven't."
    ),
)
async def search_tradera(
    query: str,
    category_id: Optional[int] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict[str, Any]:
    return await tradera_client.search_tradera(
        query=query, category_id=category_id, price_min=price_min, price_max=price_max
    )


@mcp.tool(
    title="List Tradera categories",
    description="Fetch Tradera's category tree, to find category_id values for search_tradera().",
)
async def list_tradera_categories() -> dict[str, Any]:
    return await tradera_client.get_categories()


@mcp.tool(
    title="Search Facebook Marketplace",
    description=(
        "Search Facebook Marketplace. DISABLED BY DEFAULT — this requires an "
        "unofficial method that violates Facebook's Terms of Service. Returns "
        "an explanatory error unless ENABLE_FACEBOOK_SEARCH=1 is set and the "
        "stub in src/facebook_client.py has been implemented. See its docstring."
    ),
)
async def search_facebook_marketplace(
    query: str,
    location: Optional[str] = None,
    radius_km: int = 40,
) -> dict[str, Any]:
    return await facebook_client.search_facebook(query=query, location=location, radius_km=radius_km)


@mcp.tool(
    title="Search all sources",
    description=(
        "Search Blocket + Tradera (+ Facebook Marketplace if enabled) in one call "
        "and return combined, normalized results. Use this for the weekly sourcing "
        "sweep instead of calling each source separately."
    ),
)
async def search_all(
    query: str,
    blocket_category: Optional[str] = None,
    tradera_category_id: Optional[int] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict[str, Any]:
    blocket_res = await blocket_client.search_blocket(query=query, category=blocket_category)
    tradera_res = await tradera_client.search_tradera(
        query=query, category_id=tradera_category_id, price_min=price_min, price_max=price_max
    )

    combined: list[dict[str, Any]] = []
    combined.extend(blocket_res.get("ads", []))
    combined.extend(tradera_res.get("items", []))

    fb_res = None
    if facebook_client.facebook_search_enabled():
        fb_res = await facebook_client.search_facebook(query=query)
        combined.extend(fb_res.get("listings", []) if isinstance(fb_res, dict) else [])

    return {
        "query": query,
        "total_results": len(combined),
        "results": combined,
        "source_errors": {
            k: v.get("error")
            for k, v in {"blocket": blocket_res, "tradera": tradera_res, "facebook": fb_res or {}}.items()
            if isinstance(v, dict) and v.get("error")
        },
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
