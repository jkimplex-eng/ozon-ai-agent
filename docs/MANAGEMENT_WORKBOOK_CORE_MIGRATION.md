# Management Workbook Core Migration

## Summary

Migrated 5 core daily operations tabs from ollama-bot to ozon-ai-agent.

## Tabs Added

| Tab | Columns | Mode | Data Source |
|-----|---------|------|-------------|
| **Products** | Name, SKU, Offer ID, Price, Stock | replace | DB: products + stocks / files |
| **Stocks** | Name, SKU, Offer ID, Stock | replace | DB: products + stocks / files |
| **Daily Summary** | Date, Revenue, Payout, Orders, Commission, Logistics, Advertising, COGS, Profit, Margin, DRR | replace | DB: finance / files |
| **Daily Control** | Date, Day, Orders, Revenue, Advertising, COGS, Logistics, Gross Profit, Margin, Plan VP, Deviation, Cumulative VP, Run Rate, Status, Comment | replace | DB: finance / files |
| **Daily Input** | Date, Day, Orders, Revenue, Commission, Advertising, COGS, Logistics, Partner Services, FBO Services, Gross Profit, Margin, Plan VP, Deviation, Cumulative VP, Run Rate, Status, Comment | replace | DB: finance / files |

## Columns Preserved from ollama-bot

### Daily Summary
- Дата → Date
- Выручка → Revenue
- Выплата Ozon → Payout
- Заказы → Orders
- Комиссия → Commission
- Логистика → Logistics
- Реклама → Advertising
- Себестоимость → COGS
- Прибыль → Profit
- Маржа → Margin
- ДРР → DRR

### Daily Control
- Дата → Date
- День → Day (Russian weekday: Пн/Вт/Ср/Чт/Пт/Сб/Вс)
- Заказы ₽ → Orders
- Продажи ₽ → Revenue
- Реклама ₽ → Advertising
- Себестоимость ₽ → COGS
- Доставка до МП ₽ → Logistics
- ВП ₽ → Gross Profit
- Маржа ВП % → Margin
- План ВП/день → Plan VP (from DAILY_CONTROL_PLAN_VP env)
- Отклонение ₽ → Deviation (GP - Plan)
- Накоп. ВП ₽ → Cumulative VP
- Run-rate прогноз ₽ → Run Rate
- Статус → Status (OK / BELOW PLAN)
- Комментарий → Comment

### Daily Input
- All Daily Control columns +
- Комиссия Ozon ₽ → Commission
- Услуги партнёров ₽ → Partner Services
- Услуги FBO ₽ → FBO Services

## Files Changed

| File | Change |
|------|--------|
| `src/ozon_agent/sheets/exporters/products.py` | NEW — Products exporter |
| `src/ozon_agent/sheets/exporters/stocks.py` | NEW — Stocks exporter |
| `src/ozon_agent/sheets/exporters/daily_summary.py` | NEW — Daily Summary exporter |
| `src/ozon_agent/sheets/exporters/daily_control.py` | NEW — Daily Control exporter |
| `src/ozon_agent/sheets/exporters/daily_input.py` | NEW — Daily Input exporter |
| `src/ozon_agent/sheets/setup.py` | UPDATED — 5 new tabs + colors |
| `src/ozon_agent/sheets/sync.py` | UPDATED — 5 new exporters registered |
| `tests/test_management_workbook.py` | NEW — 20 tests |
| `docs/MANAGEMENT_WORKBOOK_CORE_MIGRATION.md` | NEW — this document |

## Tests

```
tests/test_management_workbook.py — 20 tests
tests/test_sheets.py — 10 tests (existing)
tests/test_sheets_sync_file_fallback.py — 27 tests (existing)
tests/test_sheets_rate_limit_retry.py — 17 tests (existing)
tests/test_deploy.py — 25 tests (existing)
tests/test_deploy_health.py — 11 tests (existing)
tests/test_vps_deploy_pipeline.py — 19 tests (existing)
```

## What Was NOT Migrated

| Component | Reason |
|-----------|--------|
| Performance Campaigns | Requires Performance API client |
| Performance Stats | Requires Performance API CSV parser |
| Ads Budget Plan | Requires ads optimizer engine |
| Replenishment Plan | Requires replenishment engine |
| SKU Dashboard | Requires sales + performance + COGS integration |
| P&L Summary | Requires daily P&L engine (Phase 1) |
| COGS Mapping tab | Manual management — use Telegram commands instead |
| Monthly sheet cloning | Daily Input in ollama-bot uses template clone — not implemented |
| Apps Script webhook | Replaced by gspread direct API (better) |
| Freeform `/sheet` command | Security risk — not migrated |
