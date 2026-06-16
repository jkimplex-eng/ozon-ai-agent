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
ozon-agent research ingest data/raw/competitors.json --query "sj11"
```

`research sample` runs a deterministic in-memory example and demonstrates output shape.

`research ingest` validates a local JSON or CSV snapshot and converts rows into
`ResearchObservation` objects. It does not fetch pages and does not persist or mutate Ozon data.

Supported row fields include:

- `sku`, `offer_id`, `offerId`, `product_id`, `productId`
- `product_name`, `productName`, `name`, `title`
- `seller_name`, `sellerName`, `seller`
- `source_url`, `sourceUrl`, `url`
- `observed_at`, `observedAt`
- `price`, `rating`, `review_count`, `reviewCount`, `position`, `rank`, `available`

## Future Integrations

- Firecrawl extraction for competitor pages.
- Ozon seller/search browser capture.
- MCP marketplace research tools.
- Decision Engine enrichment with observed competitor context.
