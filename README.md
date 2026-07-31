# Sverige Begagnad MCP

A personal MCP server for local use (Claude Desktop / Claude Code) that searches
for quality second-hand items on **Blocket** and **Tradera** (and optionally
**Facebook Marketplace**), for a small flip loppis focused on Växjö/Älmhult.

**Not publicly listed or monetized** — use it locally only, via MCP config.

## Source status

| Source | Method | Stability |
|---|---|---|
| Tradera | Official API (SOAP v3) | Solid — tested live against the current WSDL; requires free registration |
| Blocket | Community package (`blocket-api`) | Semi-stable, unofficial — tested live against the real API |
| Facebook Marketplace | **Disabled by default** | Risky — see `src/facebook_client.py` |

## Installation

```bash
cd sverige-begagnad-mcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 1. Tradera Developer account

1. Go to https://api.tradera.com/ and register (free)
2. Accept the Terms of Use + Logo Terms of Use
3. Copy the numeric `App ID` and the `App Key` (GUID secret) into `.env`

### 2. Test Tradera on its own before connecting to Claude

```bash
python -m src.tradera_client
```

You should get back a few JSON results. The client has been tested live against
the current WSDL, so it should work immediately with valid credentials. If you
do get an error about unknown SOAP fields (SOAP APIs occasionally rename
fields), open `https://api.tradera.com/v3/searchservice.asmx?WSDL` in a browser
and compare the field names with those in `_normalize_item()` in
`src/tradera_client.py`.

Note: categories are served by *publicservice*, while search is served by
*searchservice* — both require an `AuthenticationHeader` **and** a
`ConfigurationHeader`. `PriceMaximum=0` means "max price 0 kr" (zero results),
so "no upper bound" is sent as a large sentinel value instead.

### 3. Test Blocket on its own

```bash
python3 -c "
import asyncio
from src.blocket_client import search_blocket
print(asyncio.run(search_blocket('String hylla')))
"
```

This has been verified live against the real Blocket API (results come back
under the `docs` key, and the price under `price.amount`).

### 4. Add to Claude Desktop

In Claude Desktop's MCP config file:

```json
{
  "mcpServers": {
    "sverige-begagnad": {
      "command": "/path/to/sverige-begagnad-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/sverige-begagnad-mcp",
      "env": {
        "TRADERA_APP_ID": "...",
        "TRADERA_APP_KEY": "..."
      }
    }
  }
}
```

Restart Claude Desktop. You should see the tools `search_blocket`,
`search_tradera`, `search_all`, etc. available in the conversation.

## Available tools

- `search_blocket(query, category?, max_pages?)`
- `list_blocket_categories()`
- `search_tradera(query, category_id?, price_min?, price_max?)`
- `list_tradera_categories()`
- `search_facebook_marketplace(...)` — disabled by default
- `search_all(query, ...)` — combines Blocket + Tradera (+ FB if enabled)

## Important limitation: geographic radius

Blocket filters only by **region** (län), not by an exact radius in km. By
default it searches Kronoberg + neighboring counties. For the precise "30 min
drive from Växjö" filter, the prompt used in the conversation with Claude has to
do the final check on each candidate listing itself — the results include each
ad's text location plus `coordinates` (lat/lon) and Blocket's own `distance` to
make that easier.

## Facebook Marketplace — why it's disabled

There is no public API for Facebook Marketplace. The only known methods (session
cookies or headless-browser scraping) explicitly violate Facebook's Terms of
Service. The `src/facebook_client.py` module is intentionally left as a stub,
with an explanation of how you could implement it yourself, at your own risk, if
you decide to go further.

## Extending / maintenance

If Blocket or Tradera change their internal API and the tools start failing,
check:
- Blocket: https://pypi.org/project/blocket-api/ for a newer version
- Tradera: the current WSDL schema at the URLs in `tradera_client.py`
