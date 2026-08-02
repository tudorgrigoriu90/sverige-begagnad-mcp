"""
Sverige Begagnad MCP — personal-use MCP server for sourcing quality second-hand
items on Blocket, Tradera, Klaravik, Vinted, and (optionally) Facebook
Marketplace, to flip for profit around Växjö / Älmhult.

Run locally via stdio (see README.md for Claude Desktop config):
    python -m sverige_begagnad_mcp.server
"""
# NOTE: no `from __future__ import annotations` here — FastMCP reads the
# Annotated[..., Field(...)] parameter metadata at runtime to build the tool
# input schemas, and stringized annotations would hide the Field descriptions.
from typing import Annotated, Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import Field

load_dotenv()

from . import (  # noqa: E402
    blocket_client,
    tradera_client,
    facebook_client,
    klaravik_client,
    vinted_client,
)

mcp = FastMCP("sverige-begagnad")

# Shared parameter descriptions (kept identical where the meaning is identical).
_QUERY = "Free-text search query. Swedish terms work best (e.g. 'String hylla', 'Festool', 'Fjällräven')."
_PRICE_MIN = "Optional lower price bound in SEK (inclusive). Omit for no lower bound."
_PRICE_MAX = "Optional upper price bound in SEK (inclusive). Omit for no upper bound."


@mcp.tool(
    title="Search Blocket",
    description=(
        "Search Blocket.se — Sweden's largest classifieds — for used items from private "
        "sellers and dealers. Best for LOCAL deals (usually pickup): each result carries "
        "the ad's text location plus `coordinates` (lat/lon) and `distance`, so you can "
        "apply a precise radius filter yourself (Blocket's own filter is regional/län, "
        "not km). "
        "USE for local or regional finds. Do NOT use for nationwide auctions (use "
        "search_tradera or search_klaravik), for second-hand fashion (use search_vinted), "
        "or when you want every source at once (use search_all). "
        "Returns {ads: [normalized listings], count, warning?}; each listing has "
        "source, id, title, price_sek, location, coordinates, distance, url, image_url."
    ),
)
async def search_blocket(
    query: Annotated[str, Field(description=_QUERY)],
    category: Annotated[
        Optional[str],
        Field(description="Optional Blocket category name to filter by. Must be a value from list_blocket_categories(); an unknown value is ignored and flagged in `warning`."),
    ] = None,
    locations: Annotated[
        Optional[list[str]],
        Field(description="Optional list of region (län) names to search, e.g. ['KRONOBERG','KALMAR']. Valid names come from list_blocket_locations(). If omitted, falls back to the BLOCKET_LOCATIONS env default, then to all of Sweden."),
    ] = None,
    max_pages: Annotated[
        int,
        Field(description="How many result pages to fetch (~60 ads per page). Keep small (1–3) to limit load.", ge=1, le=10),
    ] = 2,
) -> dict[str, Any]:
    return await blocket_client.search_blocket(
        query=query, category=category, locations=locations, max_pages=max_pages
    )


@mcp.tool(
    title="List Blocket categories",
    description=(
        "List the valid Blocket category names accepted by search_blocket()'s `category` "
        "argument (and search_all's `blocket_category`). Call this first when you intend "
        "to filter a Blocket search by category. Takes no arguments. Returns "
        "{categories: [names]}."
    ),
)
def list_blocket_categories() -> dict[str, Any]:
    return {"categories": blocket_client.list_categories()}


@mcp.tool(
    title="List Blocket regions",
    description=(
        "List the valid Blocket region (län) names accepted by search_blocket()'s "
        "`locations` argument (and search_all's `blocket_locations`). Takes no arguments. "
        "Returns {locations: [names]}."
    ),
)
def list_blocket_locations() -> dict[str, Any]:
    return {"locations": blocket_client.list_locations()}


@mcp.tool(
    title="Search Tradera",
    description=(
        "Search Tradera.com — Sweden's largest online auction house — via its official "
        "REST API. NATIONAL and ships anywhere; covers timed auctions and Buy-It-Now. "
        "`price_sek` is the current bid or Buy-It-Now price and CAN RISE before an auction "
        "ends. "
        "USE for nationwide, shippable finds and auctions. Do NOT use for local-pickup-only "
        "deals (use search_blocket) or for fashion (use search_vinted). "
        "Requires TRADERA_APP_ID and TRADERA_APP_KEY env vars (register free at "
        "api.tradera.com); without them it returns an error. "
        "Returns {items: [normalized listings], count, total_available}."
    ),
)
async def search_tradera(
    query: Annotated[str, Field(description=_QUERY)],
    category_id: Annotated[
        Optional[int],
        Field(description="Optional Tradera category id to filter by. Get valid ids from list_tradera_categories()."),
    ] = None,
    price_min: Annotated[Optional[int], Field(description=_PRICE_MIN)] = None,
    price_max: Annotated[Optional[int], Field(description=_PRICE_MAX)] = None,
    county_id: Annotated[
        Optional[int],
        Field(description="Optional Tradera county id to restrict results to a region. Get ids from list_tradera_counties(). Rarely needed since Tradera ships nationally."),
    ] = None,
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
    description=(
        "Fetch Tradera's full category tree to find `category_id` values for "
        "search_tradera(). Takes no arguments. Requires Tradera credentials. Returns "
        "{categories: <nested tree>} (or {error} if credentials are missing/invalid)."
    ),
)
async def list_tradera_categories() -> dict[str, Any]:
    return await tradera_client.get_categories()


@mcp.tool(
    title="List Tradera counties",
    description=(
        "Fetch Tradera's county list (id → name) for search_tradera()'s optional "
        "`county_id` filter. Takes no arguments. Rarely needed since Tradera is national. "
        "Requires Tradera credentials. Returns {counties: [...]}"
    ),
)
async def list_tradera_counties() -> dict[str, Any]:
    return await tradera_client.get_counties()


@mcp.tool(
    title="Search Klaravik",
    description=(
        "Search Klaravik.se, a Swedish online AUCTION house — the strongest source for "
        "undervalued tools, machinery, and estate/house-clearance goods. National; lots "
        "either ship or need pickup/freight (many are heavy). `price_sek` is the current "
        "bid and CAN RISE before close. "
        "USE for tools, machinery, and bulky bargains. Do NOT use for fashion (use "
        "search_vinted) or when you specifically want private-seller classifieds (use "
        "search_blocket). Unofficial endpoint — may break if the site changes. "
        "Returns {items: [normalized listings], count, total_available}."
    ),
)
async def search_klaravik(
    query: Annotated[str, Field(description=_QUERY + " Matches within item titles (e.g. 'bahco', 'cykel').")],
) -> dict[str, Any]:
    return await klaravik_client.search_klaravik(query=query)


@mcp.tool(
    title="Search Vinted",
    description=(
        "Search Vinted.se, a peer-to-peer second-hand FASHION marketplace — best for "
        "branded clothing, genuine leather/wool, bags, footwear, and outdoor apparel "
        "(e.g. Fjällräven, The North Face, Patagonia). National; items ship. Fixed prices: "
        "`price_sek` is the item price and `total_price_sek` includes Vinted's "
        "buyer-protection fee. "
        "USE for fashion and apparel. Do NOT use for furniture, tools, or electronics "
        "(use the other sources). Unofficial and bot-protected — the most fragile source; "
        "may occasionally be rate-limited and return an error. "
        "Returns {items: [normalized listings], count, total_available}."
    ),
)
async def search_vinted(
    query: Annotated[str, Field(description=_QUERY)],
    price_min: Annotated[Optional[int], Field(description=_PRICE_MIN)] = None,
    price_max: Annotated[Optional[int], Field(description=_PRICE_MAX)] = None,
) -> dict[str, Any]:
    return await vinted_client.search_vinted(query=query, price_min=price_min, price_max=price_max)


@mcp.tool(
    title="Search Facebook Marketplace",
    description=(
        "Search Facebook Marketplace for local listings. DISABLED BY DEFAULT and "
        "LOCAL-ONLY: it uses an unofficial method that violates Facebook's Terms of "
        "Service, so it returns an explanatory 'disabled' error unless "
        "ENABLE_FACEBOOK_SEARCH=1 is set locally. When enabled, it is best for local "
        "private-seller deals; otherwise prefer search_blocket for local classifieds and "
        "search_all for a full sweep. "
        "Returns {listings: [...], count} when enabled, otherwise {error, message}."
    ),
)
async def search_facebook_marketplace(
    query: Annotated[str, Field(description=_QUERY)],
    location: Annotated[
        Optional[str],
        Field(description="Optional Facebook Marketplace location id (numeric) to search in. If omitted, uses the logged-in account's saved location."),
    ] = None,
    radius_km: Annotated[
        int,
        Field(description="Advisory search radius in km. Facebook applies the radius from the account's saved location, so this is not strictly enforced.", ge=1),
    ] = 40,
) -> dict[str, Any]:
    return await facebook_client.search_facebook(query=query, location=location, radius_km=radius_km)


@mcp.tool(
    title="Search all sources",
    description=(
        "One-call sweep across ALL marketplaces — Blocket + Tradera + Klaravik + Vinted "
        "(+ Facebook Marketplace if locally enabled) — returning a single combined, "
        "normalized result set. "
        "USE this for a broad sourcing sweep when you want maximum coverage in one call. "
        "Do NOT use it when you already know the single best source for a query — call that "
        "tool directly instead (faster, fewer irrelevant results). "
        "Per-source failures are non-fatal: they are reported in `source_errors` rather "
        "than raised. Price bounds apply to the Tradera and Vinted portions. "
        "Returns {query, total_results, results: [mixed listings, each with a `source` "
        "field], source_errors}."
    ),
)
async def search_all(
    query: Annotated[str, Field(description=_QUERY)],
    blocket_category: Annotated[
        Optional[str],
        Field(description="Optional Blocket category filter for the Blocket portion (see list_blocket_categories())."),
    ] = None,
    blocket_locations: Annotated[
        Optional[list[str]],
        Field(description="Optional list of Blocket region names scoping the Blocket portion (see list_blocket_locations()). Defaults to the BLOCKET_LOCATIONS env / all Sweden."),
    ] = None,
    tradera_category_id: Annotated[
        Optional[int],
        Field(description="Optional Tradera category id for the Tradera portion (see list_tradera_categories())."),
    ] = None,
    price_min: Annotated[Optional[int], Field(description=_PRICE_MIN + " Applied to the Tradera and Vinted portions.")] = None,
    price_max: Annotated[Optional[int], Field(description=_PRICE_MAX + " Applied to the Tradera and Vinted portions.")] = None,
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
