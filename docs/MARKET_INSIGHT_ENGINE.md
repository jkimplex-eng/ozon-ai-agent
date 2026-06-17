# Market Insight Engine

The Market Insight Engine interprets stored marketplace snapshots, competitor history, detected
changes, and trends.

It does not make decisions and does not execute actions. Its output is market context for later
Decision Engine integration.

## Lifecycle

1. Local JSON/CSV or Firecrawl ingestion creates market snapshots.
2. The Knowledge Base stores snapshots under `data/market_knowledge/snapshots`.
3. The Insight Engine compares the latest snapshots and inspects historical trends.
4. Detectors produce `MarketInsight`, `MarketSignal`, `MarketRisk`, and `MarketOpportunity`.
5. Generated insights are persisted through the existing Insight Store.

## Insight Types

- `PRICE_DROP`
- `PRICE_INCREASE`
- `RATING_CHANGE`
- `REVIEW_SURGE`
- `REVIEW_DROP`
- `NEW_COMPETITOR`
- `COMPETITOR_DISAPPEARED`
- `ASSORTMENT_GAP`
- `CATEGORY_PRESSURE`
- `MARKET_GROWTH_SIGNAL`
- `MARKET_DECLINE_SIGNAL`

## Scoring

Scores are bounded to `0-100` and use:

- magnitude of change;
- number of competitors or observed events;
- historical trend length;
- competitor identity availability.

Priorities:

- `LOW`: score `<35`
- `MEDIUM`: `35-64`
- `HIGH`: `65-84`
- `CRITICAL`: `85+`

## CLI

```bash
ozon-agent research insights generate
ozon-agent research insights latest
ozon-agent research insights risks
ozon-agent research insights opportunities
```

`generate` persists generated insights. `risks` and `opportunities` calculate read-only views from
current stored snapshots.

## Safety

No Ozon API execution, HTTP requests, Telegram integration, MCP execution, product changes, stock
changes, price changes, or autonomous actions are performed by this engine.
