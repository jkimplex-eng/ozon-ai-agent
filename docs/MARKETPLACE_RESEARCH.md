# Marketplace Research Engine

The marketplace research layer is a read-only foundation for competitor and market context.

It prepares the agent to compare seller data against external marketplace observations without
performing browser automation, HTTP requests, Firecrawl calls, or Ozon API mutations.

## Scope

- Register marketplace research sources.
- Normalize supplied observations into snapshots.
- Compare own SKU observations with competitor observations.
- Generate basic price, rating, review, assortment, and data-quality insights.
- Expose CLI discovery commands.

## Safety

This layer does not fetch external pages. Planned sources such as `ozon_search`,
`ozon_product_page`, and `firecrawl` are registered as future integrations only.

The first active source is `manual`, which means tests, fixtures, or already captured data can be
passed to pure Python functions.

## CLI

```bash
ozon-agent research sources
ozon-agent research sample
```

`research sample` runs a deterministic in-memory example and demonstrates output shape.

## Future Integrations

- Firecrawl extraction for competitor pages.
- Ozon seller/search browser capture.
- MCP marketplace research tools.
- Decision Engine enrichment with observed competitor context.
