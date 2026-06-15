# CURRENT_STATE.md

## Last Updated

2026-06-14

## Completed Features

### Phase 1-3: Data, Analytics, Forecasting
- PostgreSQL schema, ETL sync, diagnostics, factor analysis
- Prophet, XGBoost, LightGBM forecasters, stock/ROI predictors

### Phase 4: Decision Engine
- Feature store, opportunity detector, confidence/risk engines
- CLI: `ozon-agent recommendations` with --sku, --top, --json, --output, --save-pending, --calibrated

### Phase 4.5: Approval Workflow
- Stored recommendations with lifecycle state machine
- CLI: `ozon-agent approvals list/show/approve/reject/mark-executed/mark-observed/close/outcomes`
- Telegram bot: `/recommendations approve <id>`, `/recommendations reject <id> <reason>`
- Migration: `migrations/002_recommendations_approval.sql`

### Phase 4.6: Outcome Learning
- Learning samples from observed recommendations + outcomes
- Accuracy metrics: percentage error, direction accuracy, success rate
- Confidence calibration: historical factor by action/SKU/risk level
- Backtesting: success rate, error analysis, profit lift estimation
- CLI: `ozon-agent learning summary/calibrate/backtest/by-action/by-sku`

### Deploy Layer
- Supervisor with forbidden keyword scanning across all modules
- Deployer blocks on forbidden keywords, detects migrations
- Migration runner: `ozon-agent migrate`, `ozon-agent migrate-status`

## Verification

- ruff: All checks passed
- mypy: 2 expected errors (telegram optional dependency)
- pytest: 84/84 pass (excluding subprocess-hanging test)
