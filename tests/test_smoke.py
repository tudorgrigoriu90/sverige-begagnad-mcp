"""
Live smoke tests — assert each source still returns data.

These hit the real marketplaces (the sources are unofficial and break when the
sites change), so they need network access. Run locally with Tradera creds set,
or in CI on a schedule. Tradera is skipped without credentials; Vinted is
skipped on a 403/429 (its bot protection blocks datacenter/CI IPs — that's an
IP issue, not a real breakage).

    pytest -v tests/
"""
import os

import pytest

from sverige_begagnad_mcp import (
    blocket_client,
    klaravik_client,
    tradera_client,
    vinted_client,
)


async def test_blocket_returns_results():
    res = await blocket_client.search_blocket("cykel", max_pages=1)
    assert not res.get("error"), res.get("error")
    assert res["count"] > 0


async def test_klaravik_returns_results():
    res = await klaravik_client.search_klaravik("cykel", max_results=5)
    assert not res.get("error"), res.get("error")
    assert res["count"] > 0


@pytest.mark.skipif(
    not (os.environ.get("TRADERA_APP_ID") and os.environ.get("TRADERA_APP_KEY")),
    reason="TRADERA_APP_ID / TRADERA_APP_KEY not set",
)
async def test_tradera_returns_results():
    res = await tradera_client.search_tradera("cykel", max_results=5)
    assert not res.get("error"), res.get("error")
    assert res["count"] > 0


async def test_vinted_returns_results():
    res = await vinted_client.search_vinted("jacka", max_results=5)
    err = res.get("error") or ""
    if "403" in err or "429" in err:
        pytest.skip(f"Vinted blocked from this IP (expected on CI/datacenter): {err}")
    assert not res.get("error"), res.get("error")
    assert res["count"] > 0
