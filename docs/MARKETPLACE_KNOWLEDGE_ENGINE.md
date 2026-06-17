# Marketplace Knowledge Engine

The Marketplace Knowledge Engine stores expert Ozon knowledge as local rules and applies those
rules as explanatory context for recommendations.

It does not execute actions, change prices, change ads, call Ozon APIs, use Telegram, or modify the
Approval Workflow.

## Domains

- `SEO`
- `RANKING`
- `ADS`
- `CONTENT`
- `PRICING`
- `LOGISTICS`
- `REVIEWS`
- `EXPERIMENTS`

## Storage

Rules live in:

```text
knowledge/<domain>/rules.yaml
```

Experiment knowledge lives in:

```text
knowledge/experiments/experiments.yaml
```

## Engine

Main functions:

- `load_rules()`
- `save_rule()`
- `list_rules()`
- `search_rules()`
- `list_domains()`
- `evaluate_rules()`
- `find_relevant_rules()`
- `build_knowledge_context()`

## Decision Integration

Recommendations now include:

- `knowledge_signals`
- `knowledge_rules`
- `knowledge_sources`

Explain mode shows these alongside internal metrics and market insights.

## CLI

```bash
ozon-agent knowledge domains
ozon-agent knowledge rules
ozon-agent knowledge search CTR
ozon-agent knowledge explain --query CTR
ozon-agent recommendations explain
```

## Initial Rules

The initial rule set covers:

- missing high-frequency search phrases in titles;
- missing searchable characteristics;
- CTR and conversion influence on ranking;
- stock availability influence on ranking;
- high CTR with low conversion as a card quality signal;
- price premium above market;
- competitor review growth;
- safe experiment framing.
