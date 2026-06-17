# Experiment Learning Engine

Experiment Learning Engine is a local, read-only learning layer for Ozon AI Agent.
It stores hypotheses, experiment records, outcomes, similarity matches, aggregate
statistics, and learning insights. It does not execute marketplace actions and does
not call Ozon APIs.

## Lifecycle

1. A recommendation can be converted into a hypothesis.
2. The hypothesis can be represented as a file-based experiment.
3. Outcomes are recorded with before/after metrics and expected deltas.
4. The learning engine classifies the result as `SUCCESS`, `PARTIAL_SUCCESS`,
   `FAILURE`, or `UNKNOWN`.
5. Similar experiments and aggregate insights enrich future recommendations.

## Storage

Local storage lives under:

```text
data/experiments/
  hypotheses/
  experiments/
  outcomes/
  insights/
  statistics/
```

The root can be overridden with `OZON_AGENT_EXPERIMENT_ROOT`, which is useful for
tests and isolated local runs.

## Hypotheses

Hypotheses include:

- SKU
- experiment type
- statement
- expected effect
- success criteria
- category/subcategory/product type context

Example:

```text
Statement: Lower price by 5%
Expected effect: orders +10%, profit not below current baseline
```

## Outcome Tracking

Supported metrics include orders, revenue, profit, CTR, CR, position, rating,
reviews, DRR, ROI, margin, and stock turnover. The outcome tracker calculates
percentage deltas and classifies success.

Rules:

- orders and profit both positive against expectation -> `SUCCESS`
- orders improve but profit falls -> `PARTIAL_SUCCESS`
- orders decline -> `FAILURE`
- missing comparable metrics -> `UNKNOWN`

## Similarity Search

Similarity uses:

- category
- subcategory
- experiment type
- price range
- shop size
- period
- product type
- change size

The result is a ranked list of `SimilarityMatch` records with score and reasons.

## Learning Insights

Learning insights summarize repeated outcomes:

```text
Category: Rugs
Type: PRICE_CHANGE
Experiments: 12
Success rate: 75%
Average orders lift: +14.2%
Average profit lift: +5.8%
```

## Decision Integration

Recommendations are enriched with:

- `learning_signals`
- `similar_experiments`
- `historical_success_rate`
- `learning_insights`
- `recommended_confidence`

`ozon-agent recommendations explain` includes a `Learning` block when historical
experiment evidence is available.

## CLI

```bash
ozon-agent experiments hypotheses
ozon-agent experiments similar <id>
ozon-agent experiments insights
ozon-agent experiments stats
```

Existing DB-backed experiment workflow commands remain unchanged.

## Safety

This layer does not:

- change prices;
- change ad bids or budgets;
- change stock;
- call live Ozon APIs;
- call Telegram;
- execute MCP tools.
