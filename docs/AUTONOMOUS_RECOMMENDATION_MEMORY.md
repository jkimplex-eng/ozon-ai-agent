# Autonomous Recommendation Memory

Autonomous Recommendation Memory is a local, read-only memory layer for Ozon AI
Agent recommendations. It stores recommendation decisions and observed outcomes,
then uses the history to enrich future recommendations with similar cases and
historical success rates.

## Scope

The memory layer does not execute actions, approve recommendations, change Ozon
prices, change ads, change stock, call Telegram, or call live Ozon APIs.

## Storage

Default storage:

```text
data/recommendation_memory/
  records/
  insights/
  statistics/
```

The root can be overridden with:

```text
OZON_AGENT_RECOMMENDATION_MEMORY_ROOT
```

## Recommendation Records

Each record stores:

- SKU
- action
- opportunity type
- reason
- expected effect
- actual effect when available
- confidence and risk scores
- result: `SUCCESS`, `PARTIAL_SUCCESS`, `FAILURE`, `UNKNOWN`
- success score
- source recommendation id

## Recommendation Enrichment

New recommendations are enriched with:

- `memory_signals`
- `similar_recommendations`
- `historical_action_success_rate`
- `memory_insights`
- `memory_confidence`

The explain output shows a `Recommendation memory` block when matching historical
records exist.

## CLI

```bash
ozon-agent recommendations memory stats
ozon-agent recommendations memory stats --json
ozon-agent recommendations memory search <query>
ozon-agent recommendations memory insights
ozon-agent recommendations memory refresh
```

## Future Work

The next layer can use memory across multiple shops and add stricter dedupe,
decay by age, and per-category confidence calibration.
