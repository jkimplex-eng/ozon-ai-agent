# PROJECT_CONTEXT.md

## Ozon AI Agent

Autonomous analytics and decision engine for Ozon marketplace sellers.

## Purpose

Automate data collection, analysis, forecasting, and deployment for Ozon seller operations. The agent syncs data from Ozon API, runs diagnostics, forecasts demand, and generates actionable recommendations.

## Architecture

```
Builder (AI/Manual) → Supervisor → Deployer → VPS
```

### Modules

| Module | Purpose |
|--------|---------|
| `api/` | Ozon API client (httpx) |
| `db/` | PostgreSQL connection pool (psycopg) |
| `etl/` | Data sync from Ozon API to DB |
| `analytics/` | Diagnostics, factor analysis, metrics |
| `forecast/` | Prophet, XGBoost, LightGBM forecasters |
| `decision/` | Recommendation engine, opportunity detection, confidence/risk scoring |
| `approval/` | Approval workflow, outcome tracking, state machine |
| `learning/` | Outcome learning, confidence calibration, backtesting |
| `experiments/` | A/B experiment tracking, lifecycle, metrics, evaluation |
| `telegram/` | Telegram bot for recommendation approvals and experiment management |
| `supervisor/` | Audit reports, deployment decisions, safety checks |
| `deploy/` | VPS deployment, health checks, rollback |
| `models/` | Data models (Pydantic) |

## Tech Stack

- Python 3.11+
- PostgreSQL (psycopg3)
- Click CLI + Rich output
- pandas, polars, xgboost, lightgbm, prophet
- mypy strict, ruff lint
- hatchling build

## Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 1 | Data Warehouse | Done |
| 2 | Analytics & Diagnostics | Done |
| 3 | Forecasting | Done |
| 4 | Decision Engine | Done |
| 4.5 | Approval Workflow | Done |
| 4.6 | Outcome Learning | Done |
| 5 | Autonomous Experiments | Done |

## Safety Model

- Decision Engine: recommendations only, no execution, no external API calls
- Approval Workflow: approval/rejection only, no Ozon state mutations
- Learning: read-only analysis, no Ozon actions, no external APIs
- Experiments: control-plane only, no automatic Ozon actions, no external APIs
- Telegram: approve/reject only, no price/ad/stock API mutation
- Telegram experiments: manage experiment state only, no Ozon write APIs
- Supervisor: scans for forbidden keywords in all modules
- Deployer: blocks deployment if forbidden keywords found or tests fail
