"""
Lightweight liveness checks for each marketplace source.

Because four of the five sources are unofficial and break when the sites change,
`health_check()` pings every source with a canned query and reports, per source,
whether it is still fetching data (no error AND >0 results). Used by the
`health_check` MCP tool and by the CI smoke test.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable

from . import (
    blocket_client,
    facebook_client,
    klaravik_client,
    tradera_client,
    vinted_client,
)

# Canned queries that a healthy source should return results for.
QUERIES = {
    "blocket": "cykel",
    "tradera": "cykel",
    "klaravik": "cykel",
    "vinted": "jacka",
    "facebook": "cykel",
}


async def _check(coro: Awaitable[dict[str, Any]], items_key: str) -> dict[str, Any]:
    """Await one source call and summarize it as {ok, count, latency_ms, error}."""
    start = time.perf_counter()
    try:
        res = await coro
        latency = round((time.perf_counter() - start) * 1000)
        if not isinstance(res, dict):
            return {"ok": False, "count": 0, "latency_ms": latency, "error": "non-dict response"}
        error = res.get("error")
        count = res.get("count")
        if count is None:
            count = len(res.get(items_key) or [])
        return {
            "ok": error is None and count > 0,
            "count": count,
            "latency_ms": latency,
            "error": error,
        }
    except Exception as e:  # noqa: BLE001 — a crash IS the unhealthy signal
        return {
            "ok": False,
            "count": 0,
            "latency_ms": round((time.perf_counter() - start) * 1000),
            "error": str(e),
        }


async def health_check() -> dict[str, Any]:
    """Ping every source concurrently and return a per-source health report."""
    names = ["blocket", "tradera", "klaravik", "vinted"]
    coros = [
        _check(blocket_client.search_blocket(QUERIES["blocket"], max_pages=1), "ads"),
        _check(tradera_client.search_tradera(QUERIES["tradera"], max_results=5), "items"),
        _check(klaravik_client.search_klaravik(QUERIES["klaravik"], max_results=5), "items"),
        _check(vinted_client.search_vinted(QUERIES["vinted"], max_results=5), "items"),
    ]
    sources = dict(zip(names, await asyncio.gather(*coros)))

    if facebook_client.facebook_search_enabled():
        sources["facebook"] = await _check(
            facebook_client.search_facebook(QUERIES["facebook"]), "listings"
        )
    else:
        sources["facebook"] = {"ok": None, "status": "disabled"}

    checked = [v for v in sources.values() if v.get("ok") is not None]
    return {
        "healthy": all(v["ok"] for v in checked),
        "unhealthy_sources": [k for k, v in sources.items() if v.get("ok") is False],
        "sources": sources,
    }
