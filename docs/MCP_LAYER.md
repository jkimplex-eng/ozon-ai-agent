# Ozon MCP Layer

## Purpose

The MCP layer exposes the existing Ozon API discovery stack as read-only MCP tool descriptors.

Current architecture:

```text
Skills Framework
        |
Swagger Registry
        |
Typed Clients
        |
MCP Layer
```

This phase intentionally implements discovery only. It does not execute tools, call Ozon, load tokens, or change marketplace data.

## Modules

- `src/ozon_agent/mcp/schemas.py`
  - `MCPToolDescriptor`
  - `MCPExecutionDisabledError`
- `src/ozon_agent/mcp/registry.py`
  - `register_tool()`
  - `unregister_tool()`
  - `list_tools()`
  - `get_tool()`
- `src/ozon_agent/mcp/tool_factory.py`
  - `discover_tools()`
- `src/ozon_agent/mcp/server.py`
  - `MCPServer`
- `src/ozon_agent/mcp/adapters/`
  - reserved for future transports

## Discovery

`discover_tools()` reads typed Ozon API clients from:

- `src/ozon_agent/integrations/ozon_api/client_registry.py`

Each typed client method becomes one MCP tool:

```text
products.product_info_list
stocks.product_info_stocks
orders.posting_fbs_list
```

## Tool Descriptor

Each tool contains:

- `name`
- `description`
- `category`
- `request_schema`
- `response_schema`
- `endpoint_metadata`

## CLI

```bash
ozon-agent mcp tools
ozon-agent mcp show products.product_info
ozon-agent mcp stats
```

`mcp show` supports the same short alias behavior as typed clients. For example, `products.product_info` resolves to the closest matching `product_info_*` method.

## Restrictions

This layer does not:

- execute tools
- perform HTTP requests
- read Ozon credentials
- mutate prices, stock, ads, campaigns, supplies, orders, or finance data
- add Telegram integration
- add Firecrawl integration

Any execution attempt raises `MCPExecutionDisabledError`.
