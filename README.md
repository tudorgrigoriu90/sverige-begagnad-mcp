# Sverige Begagnad MCP

A personal MCP server for local use (Claude Desktop / Claude Code) that searches
for quality second-hand items on **Blocket** and **Tradera** (and optionally
**Facebook Marketplace**), for a small flip loppis.

By default it searches **all of Sweden**; you narrow the area to your own region
via config or per-search (see [Geographic scope](#geographic-scope)).

**Not publicly listed or monetized** — use it locally only, via MCP config.

## Source status

| Source | Method | Stability |
|---|---|---|
| Tradera | Official REST API (v4) | Solid — tested live; requires free registration |
| Blocket | Community package (`blocket-api`) | Semi-stable, unofficial — tested live against the real API |
| Facebook Marketplace | **Disabled by default** | Risky — see `src/sverige_begagnad_mcp/facebook_client.py` |

## Get Tradera credentials (required for all install methods)

1. Go to https://api.tradera.com/register and register (free).
2. Accept the Terms of Use + Logo Terms of Use.
3. Create an application and copy the numeric **App ID** and the **App Key**
   (GUID secret). You'll supply these as `TRADERA_APP_ID` / `TRADERA_APP_KEY`.

Blocket needs no credentials. Facebook Marketplace is off by default.

## Installation

Every user runs their own copy with their own Tradera keys — pick whichever
method fits your client. `uvx`-based methods need [uv](https://docs.astral.sh/uv/)
installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`, or
`winget install astral-sh.uv` on Windows); no cloning or virtualenv needed.

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

Restart Claude Code and you'll have `search_blocket`, `search_tradera`,
`search_all`, etc. The plugin runs the server via `uvx` straight from GitHub.

### Option 2 — uvx (Claude Desktop or any MCP client)

Add to your client's MCP config (Claude Desktop: Settings → Developer → Edit
Config):

```json
{
  "mcpServers": {
    "sverige-begagnad": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/tudorgrigoriu90/sverige-begagnad-mcp", "sverige-begagnad-mcp"],
      "env": {
        "TRADERA_APP_ID": "...",
        "TRADERA_APP_KEY": "...",
        "BLOCKET_LOCATIONS": ""
      }
    }
  }
}
```

Once published to PyPI, the `args` simplify to just `["sverige-begagnad-mcp"]`.
Restart the client.

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

## Verify it works (optional)

From a source checkout with keys set (in `.env` or the environment):

```bash
# Tradera — official REST API v4 (https://api.tradera.com/v4, header auth)
python -m sverige_begagnad_mcp.tradera_client

# Blocket — unofficial community API
python -c "import asyncio; from sverige_begagnad_mcp.blocket_client import search_blocket; print(asyncio.run(search_blocket('String hylla')))"
```

Both are tested live. If Tradera's shape ever drifts, the OpenAPI spec is at
`https://api.tradera.com/openapi.json`.

## Publishing (maintainer notes)

- **PyPI** (enables the short `uvx sverige-begagnad-mcp`): `python -m build`
  then `twine upload dist/*`. Bump `version` in `pyproject.toml` and
  `src/sverige_begagnad_mcp/__init__.py` first.
- **Plugin marketplace**: the `.claude-plugin/marketplace.json` and
  `plugins/sverige-begagnad/` dirs make this repo itself the marketplace — no
  extra hosting. Users add it with the Option 1 commands above.

## Available tools

- `search_blocket(query, category?, locations?, max_pages?)`
- `list_blocket_categories()`
- `list_blocket_locations()` — valid region (län) names for `locations`
- `search_tradera(query, category_id?, price_min?, price_max?, county_id?)`
- `list_tradera_categories()`
- `list_tradera_counties()` — county ids for the optional `county_id` filter
- `search_facebook_marketplace(...)` — disabled by default
- `search_all(query, blocket_category?, blocket_locations?, tradera_category_id?, price_min?, price_max?)`
  — combines Blocket + Tradera (+ FB if enabled)

## Geographic scope

Searches default to **all of Sweden**. There are three ways to set the area,
in order of precedence:

1. **Per-search** — pass `locations` to `search_blocket` (or `blocket_locations`
   to `search_all`), e.g. `["KRONOBERG", "KALMAR"]`. Use `list_blocket_locations()`
   for valid names.
2. **A personal default** — set `BLOCKET_LOCATIONS` in `.env` to a comma-separated
   list of region names.
3. **Nothing set** — all of Sweden.

Blocket's filter is **regional (län)**, not a precise km radius. For a tight
"within X min drive" filter, let Claude do the final check per listing — each
result includes the ad's text location plus `coordinates` (lat/lon) and Blocket's
own `distance`. Tradera is national with shipping, so it has no radius concept
(there's an optional `county_id` filter, rarely needed).

### My own configuration (example)

My personal setup targets the Växjö / Älmhult area — Kronoberg plus the
bordering counties — via `.env` (gitignored, not part of the shipped defaults):

```dotenv
BLOCKET_LOCATIONS=KRONOBERG,KALMAR,JONKOPING,HALLAND,SKANE
```

## Relationship to Tradera's official AI plugin

Tradera publishes an official plugin marketplace,
[`tradera/ai-marketplace`](https://github.com/tradera/ai-marketplace)
(`claude plugin marketplace add tradera/ai-marketplace`). Its `tradera-api`
plugin covers **listing management** (look up an item by id, publish, end
listings, user token) but **not search** — so it doesn't replace this server's
sourcing/search use case. Both talk to the same Tradera REST API v4, so they
share the same `TRADERA_APP_ID` / `TRADERA_APP_KEY` credentials and can be used
side by side (this server to find items, the official plugin to manage your own
listings).

## Facebook Marketplace — why it's disabled

There is no public API for Facebook Marketplace. The only known methods (session
cookies or headless-browser scraping) explicitly violate Facebook's Terms of
Service. The `src/sverige_begagnad_mcp/facebook_client.py` module is intentionally left as a stub,
with an explanation of how you could implement it yourself, at your own risk, if
you decide to go further.

## Extending / maintenance

If Blocket or Tradera change their API and the tools start failing, check:
- Blocket: https://pypi.org/project/blocket-api/ for a newer version
- Tradera: the OpenAPI spec at https://api.tradera.com/openapi.json
