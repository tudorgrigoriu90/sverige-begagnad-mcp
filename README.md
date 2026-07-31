<!-- mcp-name: io.github.tudorgrigoriu90/sverige-begagnad-mcp -->

<div align="center">

# 🇸🇪 Sverige Begagnad MCP

**Find quality second-hand deals across Sweden — straight from your AI assistant.**

An MCP server that lets Claude (or any MCP client) search **Blocket**, **Tradera**,
**Klaravik**, and **Vinted** (plus optional local Facebook Marketplace) for used items
worth buying, restoring, and reselling.

[![PyPI](https://img.shields.io/pypi/v/sverige-begagnad-mcp.svg?logo=pypi&logoColor=white)](https://pypi.org/project/sverige-begagnad-mcp/)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-listed-1f6feb.svg)](https://registry.modelcontextprotocol.io/v0/servers?search=sverige-begagnad)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tradera API v4](https://img.shields.io/badge/Tradera-REST%20v4-00A46C.svg)](https://api.tradera.com/)
[![Blocket](https://img.shields.io/badge/Blocket-search-E4002B.svg)](https://www.blocket.se/)

</div>

---

## 💬 What you can ask Claude

Once connected, just talk to it:

> 🪑 *"Find String shelves (String hylla) near Växjö under 1000 SEK."*

> 🛠️ *"Search Blocket and Tradera for Festool or Makita tools I could flip for profit."*

> 🔊 *"What Bang & Olufsen speakers are on Tradera between 500 and 3000 SEK?"*

> 🚲 *"List Blocket categories, then look for quality bikes (Kronan, Crescent) in Skåne."*

> 📈 *"Do this week's sourcing sweep for Scandinavian design in Kronoberg and neighbouring counties, ranked by estimated profit."*

Claude picks the right tools, applies your filters, and hands back titles, prices,
locations, links, and images — from both marketplaces in one go.

## ✨ Features

| | |
|---|---|
| 🔎 **Four marketplaces** | Blocket + Tradera + Klaravik + Vinted, searched together or separately, normalized into one shape |
| 🎯 **Rich filters** | Price min/max, category, county (Tradera) · region + category (Blocket) |
| 📍 **Location-aware** | Every Blocket result carries `coordinates` + `distance` for precise radius filtering |
| 🌍 **General by default** | Searches all of Sweden; scope it to your area via config or per-search |
| 🧭 **Discovery tools** | List categories, regions, and counties so the agent filters intelligently |
| 🧩 **Easy install** | One-command Claude Code plugin, `uvx`, or from source — each user brings their own keys |
| ✅ **Tested live** | Every source verified end-to-end against the real APIs |

## 📊 Source status

| Source | Method | Stability |
|---|---|---|
| **Tradera** | Official REST API (v4) | 🟢 Solid — tested live; requires free registration |
| **Blocket** | Community package (`blocket-api`) | 🟡 Semi-stable, unofficial — tested live |
| **Klaravik** | Internal JSON endpoint | 🟡 Unofficial — tested live; auction current-bid prices |
| **Vinted** | Internal API (bot-protected) | 🟠 Unofficial, most fragile — works best from a residential IP |
| **Facebook Marketplace** | Disabled by default | 🔴 Risky, local-only — see `facebook_client.py` |

---

## 🔑 Get Tradera credentials (required for all install methods)

1. Register (free) at **https://api.tradera.com/register**.
2. Accept the Terms of Use + Logo Terms of Use.
3. Create an application and copy the numeric **App ID** and the **App Key**
   (GUID secret). You'll supply these as `TRADERA_APP_ID` / `TRADERA_APP_KEY`.

> Blocket needs no credentials. Facebook Marketplace is off by default.

## 📦 Installation

Every user runs their own copy with their own Tradera keys — pick whichever method
fits your client. `uvx`-based methods need [uv](https://docs.astral.sh/uv/)
installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`, or
`winget install astral-sh.uv` on Windows) — no cloning or virtualenv needed.

### Option 1 — Claude Code plugin (easiest)

```bash
claude plugin marketplace add tudorgrigoriu90/sverige-begagnad-mcp
claude plugin install sverige-begagnad@sverige-begagnad-marketplace
```

Then export your keys (the plugin passes them through to the server):

```bash
export TRADERA_APP_ID=...      # Windows PowerShell: $env:TRADERA_APP_ID="..."
export TRADERA_APP_KEY=...
export BLOCKET_LOCATIONS=      # optional; empty = all of Sweden
```

Restart Claude Code — you'll have `search_blocket`, `search_tradera`, `search_all`,
and more. The plugin runs the server via `uvx` straight from GitHub.

### Option 2 — uvx (Claude Desktop or any MCP client)

Add to your client's MCP config (Claude Desktop: **Settings → Developer → Edit Config**):

```json
{
  "mcpServers": {
    "sverige-begagnad": {
      "command": "uvx",
      "args": ["sverige-begagnad-mcp"],
      "env": {
        "TRADERA_APP_ID": "...",
        "TRADERA_APP_KEY": "...",
        "BLOCKET_LOCATIONS": ""
      }
    }
  }
}
```

`uvx` fetches the published package from PyPI on first run and caches it. Restart the client.

### Option 3 — From source (development)

```bash
git clone https://github.com/tudorgrigoriu90/sverige-begagnad-mcp
cd sverige-begagnad-mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env        # then fill in your keys
```

Point your client at the venv's `sverige-begagnad-mcp` command (or
`python -m sverige_begagnad_mcp.server`) with `cwd` set to the repo.

<details>
<summary>✅ <b>Verify it works (optional)</b></summary>

From a source checkout with keys set (in `.env` or the environment):

```bash
# Tradera — official REST API v4 (https://api.tradera.com/v4, header auth)
python -m sverige_begagnad_mcp.tradera_client

# Blocket — unofficial community API
python -c "import asyncio; from sverige_begagnad_mcp.blocket_client import search_blocket; print(asyncio.run(search_blocket('String hylla')))"
```

Both are tested live. If Tradera's shape ever drifts, the OpenAPI spec is at
`https://api.tradera.com/openapi.json`.
</details>

---

## 🧰 Tools

| Tool | Purpose |
|---|---|
| `search_blocket(query, category?, locations?, max_pages?)` | Search Blocket |
| `list_blocket_categories()` | Valid category names |
| `list_blocket_locations()` | Valid region (län) names |
| `search_tradera(query, category_id?, price_min?, price_max?, county_id?)` | Search Tradera |
| `list_tradera_categories()` | Category tree → `category_id` |
| `list_tradera_counties()` | County ids for the optional `county_id` filter |
| `search_klaravik(query)` | Search Klaravik auctions (current-bid prices) |
| `search_vinted(query, price_min?, price_max?)` | Search Vinted fashion listings |
| `search_facebook_marketplace(...)` | Disabled by default (local-only) |
| `search_all(query, blocket_category?, blocket_locations?, tradera_category_id?, price_min?, price_max?)` | Blocket + Tradera + Klaravik + Vinted in one call |

## 📍 Geographic scope

Searches default to **all of Sweden**. Three ways to set the area, in order of precedence:

1. **Per-search** — pass `locations` to `search_blocket` (or `blocket_locations` to
   `search_all`), e.g. `["KRONOBERG", "KALMAR"]`. Use `list_blocket_locations()` for valid names.
2. **A personal default** — set `BLOCKET_LOCATIONS` in `.env` to a comma-separated list of region names.
3. **Nothing set** — all of Sweden.

Blocket's filter is **regional (län)**, not a precise km radius. For a tight
"within X min drive" filter, let Claude do the final check per listing — each result
includes the ad's text location plus `coordinates` (lat/lon) and Blocket's own
`distance`. Tradera is national with shipping, so it has no radius concept (there's
an optional `county_id` filter, rarely needed).

<details>
<summary>🗺️ <b>Example: my own Växjö / Älmhult setup</b></summary>

Personal scope lives only in `.env` (gitignored — not a shipped default):

```dotenv
BLOCKET_LOCATIONS=KRONOBERG,KALMAR,JONKOPING,HALLAND,SKANE
```
</details>

<details>
<summary>🤖 <b>Power user: a full weekly "sourcing agent" prompt</b></summary>

Paste this as your instructions to turn the tools into a profit-ranked weekly sweep.
It runs many targeted Swedish searches, filters by radius/quality, estimates profit,
and returns a ranked shortlist. Tune the brands, region, and thresholds to taste.

```text
ROLE: You are a sourcing assistant for a personal, quality-focused loppis (flip).
Each week, search Blocket and Tradera for second-hand items to buy, minimally
restore, and resell at a profit.

METHOD: Search with SWEDISH terms. Run MANY targeted searches — by BRAND and by
CATEGORY — across both sources; deduplicate. Prices are in SEK.

AREA: within ~35 km straight-line of Växjö (56.88, 14.81) or Älmhult (56.55, 14.14),
computed from each Blocket result's `coordinates`. Tradera ships nationally, so
include shippable Tradera items too.

QUALITY: recognized brand or top craftsmanship (String, Artek, Fritz Hansen, Louis
Poulsen, Iittala, Orrefors, Bang & Olufsen, Braun, Marantz, Bahco, Hilti, Festool,
Makita, Kronan, Crescent…); "bra skick"/"nyskick" or minor cosmetic wear; asking
price clearly below market; only minimal restoration (clean, polish, light sand,
small off-the-shelf parts).

PROFIT: estimate resale value (use web search for comparables if available — do NOT
invent sold prices). Net = resale − (purchase + restoration + pickup/courier), with
stated assumptions (~80 SEK pickup fuel, ~70 SEK courier, 0–150 SEK materials).
Include only items with estimated net profit ≥ 300 SEK. Note that Tradera auction
prices may rise before close.

OUTPUT: ranked by net profit descending, max 15. For each: title + link + location
(distance from Växjö or "ships nationally"), asking vs. estimated market price, net
profit with assumptions, 2–3 restoration steps, and a risk note. End with a 2–3
sentence read on the week's trends. Don't pad with weak candidates.
```
</details>

---

## 🚫 Facebook Marketplace — why it's disabled

There is no public API for Facebook Marketplace. The only known methods (session
cookies or headless-browser scraping) explicitly violate Facebook's Terms of Service.
The `src/sverige_begagnad_mcp/facebook_client.py` module is intentionally left as a
stub, with an explanation of how you could implement it yourself, at your own risk.

## 🛠️ Maintenance & publishing

<details>
<summary>Maintainer notes</summary>

- **If a source breaks:** Blocket → check https://pypi.org/project/blocket-api/ for a
  newer version; Tradera → the OpenAPI spec at https://api.tradera.com/openapi.json.
- **PyPI** (enables the short `uvx sverige-begagnad-mcp`): `python -m build` then
  `twine upload dist/*`. Bump `version` in `pyproject.toml` and
  `src/sverige_begagnad_mcp/__init__.py` first.
- **Plugin marketplace:** the `.claude-plugin/marketplace.json` + `plugins/` dirs make
  this repo itself the marketplace — no extra hosting.
- **MCP Registry:** `server.json` is ready; publish with the `mcp-publisher` CLI after
  the PyPI release (see the Registry publishing guide).
</details>

## 📄 License

[MIT](LICENSE) — each user runs their own copy with their own credentials. Note that
Blocket has no official API; this uses an unofficial community package, so treat the
Blocket half accordingly.
