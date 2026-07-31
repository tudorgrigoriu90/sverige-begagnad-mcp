"""
Sverige Begagnad MCP — personal-use MCP server for sourcing quality
second-hand items on Blocket, Tradera, and (optionally) Facebook
Marketplace, to flip for profit around Växjö / Älmhult.

Run locally via stdio (see README.md for Claude Desktop config):
    python -m sverige_begagnad_mcp.server
"""
from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from . import (  # noqa: E402
    blocket_client,
    tradera_client,
    facebook_client,
    klaravik_client,
    vinted_client,
)

mcp = FastMCP("sverige-begagnad")


@mcp.tool(
    title="Search Blocket",
    description=(
        "Search Blocket.se for second-hand listings. The location filter is REGIONAL "
        "(län), not a precise km radius. Pass `locations` (region names from "
        "list_blocket_locations()) to narrow the search; if omitted it uses the "
        "BLOCKET_LOCATIONS env default, or all of Sweden if that is unset. Each result "
        "includes the ad's text location plus coordinates/distance so you can apply a "
        "precise 'within X min drive' filter yourself. Use list_blocket_categories() "
        "first if you want to filter by category."
    ),
)
async def search_blocket(
    query: str,
    category: Optional[str] = None,
    locations: Optional[list[str]] = None,
    max_pages: int = 2,
) -> dict[str, Any]:
    return await blocket_client.search_blocket(
        query=query, category=category, locations=locations, max_pages=max_pages
    )


@mcp.tool(
    title="List Blocket categories",
    description="List valid category names to pass into search_blocket()'s `category` argument.",
)
def list_blocket_categories() -> dict[str, Any]:
    return {"categories": blocket_client.list_categories()}


@mcp.tool(
    title="List Blocket regions",
    description="List valid region (län) names to pass into search_blocket()'s `locations` argument.",
)
def list_blocket_locations() -> dict[str, Any]:
    return {"locations": blocket_client.list_locations()}


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
    county_id: Optional[int] = None,
) -> dict[str, Any]:
    return await tradera_client.search_tradera(
        query=query,
        category_id=category_id,
        price_min=price_min,
        price_max=price_max,
        county_id=county_id,
    )


@mcp.tool(
    title="List Tradera categories",
    description="Fetch Tradera's category tree, to find category_id values for search_tradera().",
)
async def list_tradera_categories() -> dict[str, Any]:
    return await tradera_client.get_categories()


@mcp.tool(
    title="List Tradera counties",
    description=(
        "Fetch Tradera's county list (id -> name) for search_tradera()'s optional "
        "`county_id` filter. Tradera is national with shipping, so this is rarely needed."
    ),
)
async def list_tradera_counties() -> dict[str, Any]:
    return await tradera_client.get_counties()


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
    title="Search Klaravik",
    description=(
        "Search Klaravik.se, a Swedish online auction house — strong for undervalued "
        "tools, machinery, and house-clearance goods. Prices are the current bid (SEK) "
        "and can rise before the auction ends. Swedish search terms work best."
    ),
)
async def search_klaravik(query: str) -> dict[str, Any]:
    return await klaravik_client.search_klaravik(query=query)


@mcp.tool(
    title="Search Vinted",
    description=(
        "Search Vinted.se, a second-hand fashion marketplace — good for genuine "
        "leather/wool and branded clothing. National (ships anywhere). Unofficial and "
        "the most fragile source (bot-protected); may occasionally be rate-limited."
    ),
)
async def search_vinted(
    query: str,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict[str, Any]:
    return await vinted_client.search_vinted(query=query, price_min=price_min, price_max=price_max)


@mcp.tool(
    title="Search all sources",
    description=(
        "Search Blocket + Tradera + Klaravik + Vinted (+ Facebook Marketplace if enabled) "
        "in one call and return combined, normalized results. Use this for the weekly "
        "sourcing sweep instead of calling each source separately."
    ),
)
async def search_all(
    query: str,
    blocket_category: Optional[str] = None,
    blocket_locations: Optional[list[str]] = None,
    tradera_category_id: Optional[int] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict[str, Any]:
    blocket_res = await blocket_client.search_blocket(
        query=query, category=blocket_category, locations=blocket_locations
    )
    tradera_res = await tradera_client.search_tradera(
        query=query, category_id=tradera_category_id, price_min=price_min, price_max=price_max
    )
    klaravik_res = await klaravik_client.search_klaravik(query=query)
    vinted_res = await vinted_client.search_vinted(query=query, price_min=price_min, price_max=price_max)

    combined: list[dict[str, Any]] = []
    combined.extend(blocket_res.get("ads", []))
    combined.extend(tradera_res.get("items", []))
    combined.extend(klaravik_res.get("items", []))
    combined.extend(vinted_res.get("items", []))

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
            for k, v in {
                "blocket": blocket_res,
                "tradera": tradera_res,
                "klaravik": klaravik_res,
                "vinted": vinted_res,
                "facebook": fb_res or {},
            }.items()
            if isinstance(v, dict) and v.get("error")
        },
    }


def main() -> None:
    """Console-script entry point (see pyproject.toml [project.scripts])."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
