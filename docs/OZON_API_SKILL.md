# Ozon API Skill

## Purpose

The `ozon_api` skill is the first integration-oriented skill in the project. It uses a local Swagger artifact as the source of truth for Ozon Seller API discovery and prepares the project for future client and MCP layers.

## Skill Structure

Files under [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\skills\ozon_api](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\skills\ozon_api):

- `SKILL.md`
- `rules.md`
- `examples.md`
- `metadata.yaml`
- `swagger.json`

`swagger.json` is intentionally treated as the only API source of truth for endpoint discovery.

## Swagger Loader

Implementation lives in:

- [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\skills\ozon_api\swagger_loader.py](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\skills\ozon_api\swagger_loader.py)

Supported operations:

- `load_swagger()`
- `reload_swagger()`
- `validate_swagger()`
- `get_swagger_version()`

The loader:

- locates `ozon_api` through the existing Skills Framework
- reads `swagger.json`
- validates top-level OpenAPI structure
- builds typed endpoint models

## Registry

Implementation lives in:

- [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\skills\ozon_api\swagger_registry.py](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\skills\ozon_api\swagger_registry.py)

Supported operations:

- `list_endpoints()`
- `get_endpoint(name)`
- `search_endpoints(query)`
- `count_endpoints()`
- `count_endpoints_by_category()`

## CLI Commands

- `ozon-agent api endpoints`
- `ozon-agent api search stock`
- `ozon-agent api show product-info`
- `ozon-agent api stats`

These commands are read-only and do not perform HTTP calls.

## Categories

The current endpoint categorization supports:

- Products
- Stocks
- Prices
- Orders
- Analytics
- Finance
- Returns
- Reviews
- FBO
- FBS

Unknown or unmatched endpoints fall into `Other`.

## Future Extension

The current layer is prepared for:

- MCP server exposure
- generated Ozon API client surfaces
- request mappers and typed wrappers

The integration stubs live in:

- [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\integrations\ozon_api\client_generator.py](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\integrations\ozon_api\client_generator.py)
- [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\integrations\ozon_api\endpoint_mapper.py](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\src\ozon_agent\integrations\ozon_api\endpoint_mapper.py)

No real HTTP execution is implemented at this stage.
