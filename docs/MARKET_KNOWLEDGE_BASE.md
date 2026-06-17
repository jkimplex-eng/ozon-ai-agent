# Market Knowledge Base

The market knowledge base stores local marketplace snapshots, competitor history, derived changes,
and market insights.

It is intentionally local-only at this phase:

- no Firecrawl;
- no HTTP;
- no Ozon API calls;
- no Telegram integration;
- no marketplace mutations.

## Storage

Default storage is file-based:

```text
data/market_knowledge/
  snapshots/
  insights/
```

Snapshots and insights are JSON files. This keeps the layer reviewable and easy to migrate to
PostgreSQL later.

## Snapshots

`MarketKnowledgeSnapshot` stores:

- snapshot id;
- query;
- source name;
- capture timestamp;
- normalized competitor observations.

After local ingestion:

```bash
ozon-agent research ingest competitors.json --query "sj11"
```

the snapshot is automatically saved into `data/market_knowledge/snapshots`.

## History

The history layer converts snapshots into `CompetitorHistoryRecord` rows keyed by:

```text
sku + seller_name + source_url
```

This lets the agent compare the same competitor across multiple captures.

## Changes

`compare_snapshots()` and `detect_changes()` detect:

- price changes;
- rating changes;
- review count changes;
- availability changes;
- new competitors;
- disappeared competitors.

## Trends

Trend helpers inspect multiple snapshots:

- `detect_price_trend()`
- `detect_rating_trend()`
- `detect_review_trend()`
- `detect_trends()`

Each trend includes metric direction, first value, last value, absolute delta, percentage delta, and
snapshot count.

## Insights

`MarketInsightRecord` stores derived observations such as:

- competitor price decreased by 12%;
- competitor gained reviews;
- new competitor appeared.

CLI:

```bash
ozon-agent research snapshots
ozon-agent research snapshot <id>
ozon-agent research compare <snapshot_a> <snapshot_b>
ozon-agent research insights
```

`research compare` saves generated insights to `data/market_knowledge/insights`.

## Future Use

This foundation prepares market data for:

- Firecrawl ingestion;
- MCP research tools;
- Decision Engine feature enrichment;
- pricing and content experiment planning.

## Firecrawl Adapter

Firecrawl ingestion uses the hosted scrape endpoint and stores structured extraction results as
normal market snapshots.

```bash
set FIRECRAWL_API_KEY=fc-...
ozon-agent research firecrawl ingest https://example.com/product --query "sj11"
```

The adapter calls Firecrawl's `POST /v2/scrape` endpoint with markdown plus structured JSON output.
The JSON schema asks for competitor observations with SKU or offer id, product name, seller, URL,
price, rating, review count, position, and availability.

The CLI saves the result into the same snapshot store used by local JSON/CSV ingestion.

Safety notes:

- API keys are read from environment variables, not CLI arguments.
- Tests use mocked HTTP transport and do not call Firecrawl.
- No Ozon API, Telegram, MCP execution, or marketplace mutation is performed.
