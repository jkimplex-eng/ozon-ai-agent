# Management Workbook Audit

## 1. Executive Summary

**ollama-bot** has 18 Google Sheets tabs managed by 8 services via Apps Script webhook.
**ozon-ai-agent** has 8 tabs managed by gspread direct API.

**Overlap:** 2 tabs (Products, Stocks — but different approaches).
**Gap:** 16 tabs in ollama-bot not yet in ozon-ai-agent.

---

## 2. Complete Tab Inventory

### ollama-bot Tabs (18)

| # | Tab Name | Mode | Service | Data Source |
|---|----------|------|---------|-------------|
| 1 | Products | replace | jobs.js | Seller API /v2/product/list |
| 2 | Stocks | replace | jobs.js | Seller API /v4/product/info/stocks |
| 3 | Performance Campaigns | replace | performance.js | Performance API /api/client/campaign |
| 4 | Performance Stats | replace | performance.js | Performance API CSV reports |
| 5 | P&L Summary | replace | reportBuilder.js | Finance + Sales + Performance |
| 6 | SKU Dashboard | replace | reportBuilder.js | Sales + Performance + COGS |
| 7 | Ads Budget Plan | replace | adsOptimizer.js | Performance + Sales + Stock |
| 8 | COGS Mapping | replace | manual | Manual entry |
| 9 | Daily Summary | append | dailySummary.js | Finance + Postings + Performance |
| 10 | Daily Control | replace* | dailyControl.js | Sales + Finance + Performance + COGS |
| 11 | Daily Input | replace* | managementWorkbook.js | Sales + Finance + Performance + COGS |
| 12 | Replenishment Plan | replace | replenishment.js | Sales + Stock + Priority + Traffic |
| 13 | Alerts | append | alerts.js | Products + Performance |
| 14 | Daily SKU | append | dailySummary.js | Postings (per-SKU) |
| 15 | PL History | append | dailySummary.js | Finance + Postings |
| 16 | Finance Raw | append | dailySummary.js | Finance API (raw transactions) |
| 17 | Orders Raw | append | dailySummary.js | FBO/FBS postings |
| 18 | PL Diagnostics | append | dailySummary.js | Meta: counts, warnings |

*Daily Control and Daily Input use `updateByDate` — upsert by date column, not full replace.

### ozon-ai-agent Tabs (8)

| # | Tab Name | Mode | Exporter | Data Source |
|---|----------|------|----------|-------------|
| 1 | Daily Report | replace | daily_report.py | products + sales + advertising (DB) |
| 2 | Recommendations | replace | recommendations.py | approval repository (DB) |
| 3 | Market Insights | replace | market_insights.py | products (DB) + market_knowledge (files) |
| 4 | Competitors | replace | competitors.py | products (DB) + market_knowledge (files) |
| 5 | Experiments | replace | experiments.py | experiments repository (DB) |
| 6 | Recommendation Memory | replace | memory.py | learning module (DB) |
| 7 | Ingestion Status | replace | ingestion_status.py | etl_log (DB) |
| 8 | Approvals | replace | approvals.py | approval repository (DB) |

---

## 3. Per-Tab Analysis

### 3.1 Products

**ollama-bot:**
- Tab: `Products` (replace)
- Columns: Название, SKU, Offer ID, Цена, Остаток
- Source: `ozonService.getProducts()` → `/v2/product/list`
- Frequency: Every 30 min (background job)
- Writer: `jobs.js` → `sheetsService.clearAndWriteMappedRows("products", rows)`

**ozon-ai-agent:**
- Tab: `Daily Report` (partially overlaps — has SKU, revenue, quantity)
- Source: `products` + `sales` + `advertising` tables
- No dedicated Products tab

**Verdict:** NEEDS MIGRATION — add dedicated Products tab

---

### 3.2 Stocks

**ollama-bot:**
- Tab: `Stocks` (replace)
- Columns: Название, SKU, Offer ID, Остаток
- Source: `ozonService.getNormalizedStockRows()` → `/v4/product/info/stocks`
- Frequency: Every 60 min (background job)
- Writer: `jobs.js` → `sheetsService.clearAndWriteMappedRows("stocks", rows)`

**ozon-ai-agent:**
- No Stocks tab

**Verdict:** NEEDS MIGRATION

---

### 3.3 Performance Campaigns

**ollama-bot:**
- Tab: `Performance Campaigns` (replace)
- Columns: Campaign ID, Campaign Name, State, Adv Object Type, Payment Type, From Date, To Date, Budget, Daily Budget, Weekly Budget, Placement, Product Campaign Mode, Created At, Updated At
- Source: Performance API `/api/client/campaign`
- Frequency: On-demand (Telegram command)
- Writer: `performance.js` → `sheetsService.clearAndWriteMappedRows("performance_campaigns", rows)`
- Formatting: boldHeader, freezeRows, autoResize, black header, currency columns

**ozon-ai-agent:**
- No Performance Campaigns tab
- Performance API client not yet implemented

**Verdict:** NEEDS MIGRATION (requires Performance API client first)

---

### 3.4 Performance Stats

**ollama-bot:**
- Tab: `Performance Stats` (replace)
- Columns: Date, Campaign ID, Campaign Name, SKU, Product Name, Price, Impressions, Clicks, CTR, Add To Cart, Avg CPC, Spend, Orders, Revenue, Model Orders, Model Revenue, DRR, Ordered Amount, Total DRR, Added At
- Source: Performance API CSV reports
- Frequency: On-demand (after report generation)
- Writer: `performance.js` → `sheetsService.clearAndWriteMappedRows("performance_stats", rows)`
- Formatting: currency, percent, conditional columns

**ozon-ai-agent:**
- No Performance Stats tab

**Verdict:** NEEDS MIGRATION (requires Performance API client first)

---

### 3.5 P&L Summary

**ollama-bot:**
- Tab: `P&L Summary` (replace)
- Columns: Metric + dynamic date columns
- Rows: Заказано, Продажи, Возвраты, Реклама, Комиссия Ozon, Логистика, Услуги партнёров, Услуги FBO, Себес, Прибыль, Начислено/Выплата
- Source: Finance + Sales + Performance (aggregated)
- Frequency: On-demand (Telegram `/report pnl`)
- Writer: `reportBuilder.js` → `sheetsService.clearAndWriteMappedRows("pnl_summary", rows)`
- Formatting: currency rows, conditional profit (green/red)

**ozon-ai-agent:**
- No P&L Summary tab
- `Daily Report` tab has some overlap (SKU metrics)

**Verdict:** NEEDS MIGRATION

---

### 3.6 SKU Dashboard

**ollama-bot:**
- Tab: `SKU Dashboard` (replace)
- Columns: 24 columns (Название, Категория, ШК, РРЦ, Себ, Артикул, Рубли, Штуки, Цена, Реклама, ДРР, Выручка, Штуки, Цена, Реклама, ДРР, ВП, Показы общие, Показы реклама, Клики, CTR, Корзины, Позиция ср.)
- Source: Sales + Performance + COGS + Products
- Frequency: On-demand (Telegram `/report sku`)
- Writer: `reportBuilder.js` → `sheetsService.clearAndWriteMappedRows("sku_dashboard", rows)`
- Formatting: currency, percent, conditional ВП (green/red)

**ozon-ai-agent:**
- No SKU Dashboard tab
- `Daily Report` tab has partial overlap (SKU, revenue, quantity, DRR, margin)

**Verdict:** NEEDS REWRITE — current Daily Report is simpler, needs expansion

---

### 3.7 Ads Budget Plan

**ollama-bot:**
- Tab: `Ads Budget Plan` (replace)
- Columns: Month, Date From, Date To, Offer ID, SKU, Campaign ID, Campaign Name, Current Spend, Recommended Delta, Planned Spend Preview, Revenue, GP, Margin, DRR/ACOS, Stock Days, Priority, Decision, Reason, Expected Effect, Confidence, Stop-loss
- Source: Performance + Sales + Stock (via skuDayService)
- Frequency: On-demand (Telegram `/ads budget plan`)
- Writer: `adsOptimizer.js` → `sheetsService.clearAndWriteMappedRows("ads_budget_plan", rows)`
- Formatting: currency, percent, conditional GP (green/red)

**ozon-ai-agent:**
- No Ads Budget Plan tab

**Verdict:** NEEDS MIGRATION (Phase 2 — ads optimizer)

---

### 3.8 COGS Mapping

**ollama-bot:**
- Tab: `COGS Mapping` (replace)
- Columns: SKU, Offer ID, Product Name, COGS, Logistics To MP, Notes
- Source: Manual entry or import
- Frequency: Manual
- Writer: None found in audited code (likely manual or separate import)

**ozon-ai-agent:**
- No COGS tab
- COGS stored in `products.cost_price` column

**Verdict:** NEEDS MIGRATION — dedicated COGS management tab

---

### 3.9 Daily Summary

**ollama-bot:**
- Tab: `Daily Summary` (append)
- Columns: Дата, Выручка, Выплата Ozon, Заказы, Комиссия, Логистика, Реклама, Себестоимость, Прибыль, Маржа, ДРР
- Source: Finance transactions + Postings + Performance
- Frequency: On-demand (Telegram `/daily`) or cron
- Writer: `dailySummary.js` → `sheetsService.addRow("daily_summary", row)`

**ozon-ai-agent:**
- No Daily Summary tab
- `Daily Report` tab has similar data but different structure

**Verdict:** NEEDS MIGRATION

---

### 3.10 Daily Control

**ollama-bot:**
- Tab: `Daily Control` (replace via updateByDate)
- Columns: Дата, День, Заказы ₽, Продажи ₽, Реклама ₽, Себестоимость ₽, Доставка до МП ₽, ВП ₽, Маржа ВП %, План ВП/день, Отклонение ₽, Накоп. ВП ₽, Run-rate прогноз ₽, Статус, Комментарий
- Source: Sales + Finance + Performance + COGS (aggregated from month start)
- Frequency: On-demand (Telegram `/daily control`)
- Writer: `dailyControl.js` → `sheetsService.updateMappedRowByDate("daily_control", ...)`
- Key: Plan vs Actual comparison, run-rate, cumulative VP
- Formatting: currency, conditional ВП (green/red)

**ozon-ai-agent:**
- No Daily Control tab

**Verdict:** NEEDS MIGRATION — critical operational tab

---

### 3.11 Daily Input (Management Workbook)

**ollama-bot:**
- Tab: `Daily Input YYYY-MM` (replace via updateByDate, monthly cloned)
- Columns: Дата, День, Заказы ₽, Продажи ₽, Комиссия Ozon ₽, Реклама ₽, Себестоимость ₽, Доставка до МП ₽, Услуги партнёров ₽, Услуги FBO ₽, ВП ₽, Маржа ВП %, План ВП/день, Отклонение ₽, Накоп. ВП ₽, Run-rate прогноз ₽, Статус, Комментарий
- Source: Sales + Finance + Performance + COGS
- Frequency: On-demand (Telegram `/management daily`) or cron
- Writer: `managementWorkbook.js` → `sheetsService.updateMappedRowByDate("daily_input", ...)`
- Key: Monthly management sheet, cloned from template, 18 columns, formula-driven Plan/Deviation/Cumulative/Run-rate columns preserved
- Formatting: currency, conditional ВП (green/red)

**ozon-ai-agent:**
- No Daily Input tab

**Verdict:** NEEDS MIGRATION — core management tab

---

### 3.12 Replenishment Plan

**ollama-bot:**
- Tab: `Replenishment Plan` (replace)
- Columns: City, Warehouse, SKU, Offer ID, Product Name, Organic Sales Per Day, Current Stock, Days Of Stock, Organic Target Stock, External Traffic Demand ₽, External Traffic Units, Total Target Stock, Recommended Shipment, Priority, Demand Source, Comment
- Source: Sales + Stock + Priority SKUs + External Traffic Plan + Warehouse Mapping
- Frequency: On-demand (Telegram `/replenishment forecast`)
- Writer: `replenishment.js` → `sheetsService.clearAndWriteMappedRows("replenishment_plan", rows)`

**ozon-ai-agent:**
- No Replenishment Plan tab

**Verdict:** Phase 2 — complex dependencies

---

### 3.13 Alerts

**ollama-bot:**
- Tab: `Alerts` (append)
- Columns: Дата, Уровень, Тип, Сообщение
- Source: Alert detection engine
- Frequency: On alert trigger
- Writer: Not found in audited code (likely from alerts.js or error handlers)

**ozon-ai-agent:**
- No Alerts tab

**Verdict:** NEEDS MIGRATION (with alerts engine)

---

### 3.14 Daily SKU

**ollama-bot:**
- Tab: `Daily SKU` (append)
- Columns: Дата, SKU, Offer ID, Название, Количество, Выручка
- Source: Postings (per-SKU breakdown)
- Frequency: On-demand (Telegram `/daily`)
- Writer: `dailySummary.js` → `sheetsService.addRows("daily_sku", rows)`

**ozon-ai-agent:**
- No Daily SKU tab

**Verdict:** NEEDS MIGRATION

---

### 3.15 PL History

**ollama-bot:**
- Tab: `PL History` (append)
- Columns: Дата, Выручка, Выплата Ozon, Заказы, Финансовые транзакции, Отправления, Прибыль, Warnings
- Source: Finance + Postings (aggregated)
- Frequency: On-demand (Telegram `/daily`)
- Writer: `dailySummary.js` → `sheetsService.addRow("daily_history", row)`

**ozon-ai-agent:**
- No PL History tab

**Verdict:** NEEDS MIGRATION

---

### 3.16 Finance Raw

**ollama-bot:**
- Tab: `Finance Raw` (append)
- Columns: Дата отчёта, Дата операции, operation_type, operation_type_name, accruals_for_sale, sale_commission, amount, delivery_charge, return_delivery_charge, services, posting_number, sku, offer_id, item_name
- Source: Finance API (raw transactions)
- Frequency: On-demand (Telegram `/daily`)
- Writer: `dailySummary.js` → `sheetsService.addRows("finance_raw", rows)`

**ozon-ai-agent:**
- No Finance Raw tab

**Verdict:** NEEDS MIGRATION

---

### 3.17 Orders Raw

**ollama-bot:**
- Tab: `Orders Raw` (append)
- Columns: Дата отчёта, Дата отправления, Схема, posting_number, status, sku, offer_id, item_name, quantity, price, gross_revenue
- Source: FBO/FBS postings (raw)
- Frequency: On-demand (Telegram `/daily`)
- Writer: `dailySummary.js` → `sheetsService.addRows("orders_raw", rows)`

**ozon-ai-agent:**
- No Orders Raw tab

**Verdict:** NEEDS MIGRATION

---

### 3.18 PL Diagnostics

**ollama-bot:**
- Tab: `PL Diagnostics` (append)
- Columns: Дата отчёта, Дата от, Дата до, Таймзона, finance_transactions, postings, revenue, orders, payout, profit_calculated, warnings
- Source: Meta: counts and warnings from daily summary generation
- Frequency: On-demand (Telegram `/daily`)
- Writer: `dailySummary.js` → `sheetsService.addRows("pl_diagnostics", rows)`

**ozon-ai-agent:**
- No PL Diagnostics tab

**Verdict:** NEEDS MIGRATION

---

## 4. Telegram Commands That Write to Sheets

| Command | Tab Written | Service |
|---------|-------------|---------|
| `/daily` | Daily Summary, Daily SKU, PL History, Finance Raw, Orders Raw, PL Diagnostics | dailySummary.js |
| `/daily в таблицу` | Daily Input (monthly) | dailySync.js → managementWorkbook.js |
| `/daily control` | Daily Control | dailyControl.js |
| `/daily control в таблицу` | Daily Control | dailyControl.js |
| `/management daily` | Daily Input (monthly) | managementWorkbook.js |
| `/management daily в таблицу` | Daily Input (monthly) | managementWorkbook.js |
| `/management backfill` | Daily Input (monthly, range) | managementWorkbook.js |
| `/management month init` | Creates monthly tab | managementWorkbook.js |
| `/performance campaigns` | Performance Campaigns | performance.js |
| `/performance stats` | Performance Stats | performance.js |
| `/performance report` | Performance Stats | performance.js |
| `/report pnl` | P&L Summary | reportBuilder.js |
| `/report pnl в таблицу` | P&L Summary | reportBuilder.js |
| `/report sku` | SKU Dashboard | reportBuilder.js |
| `/report sku в таблицу` | SKU Dashboard | reportBuilder.js |
| `/ads budget plan` | Ads Budget Plan | adsOptimizer.js |
| `/replenishment forecast` | Replenishment Plan | replenishment.js |
| `/replenishment forecast в таблицу` | Replenishment Plan | replenishment.js |
| `/ozon товары в таблицу` | Products | jobs.js |
| `/sheet Лист1 \| val1 \| val2` | Any (freeform) | sheets.js |

---

## 5. Reuse Matrix

### Already Exists in ozon-ai-agent

| Component | Status | Notes |
|-----------|--------|-------|
| Google Sheets auth (gspread) | ✅ Exists | `sheets/client.py` — service account auth |
| Sheets sync orchestrator | ✅ Exists | `sheets/sync.py` — throttled sync |
| Sheets background scheduler | ✅ Exists | `sheets/scheduler.py` — APScheduler |
| Sheets formatting | ✅ Exists | `sheets/format.py` — headers, status colors, column widths |
| File-based fallback | ✅ Exists | `sheets/file_source.py` — DB fallback |
| Daily Report tab | ✅ Exists | SKU metrics (partial overlap with Daily Summary) |
| Recommendations tab | ✅ Exists | No overlap |
| Market Insights tab | ✅ Exists | No overlap |
| Competitors tab | ✅ Exists | No overlap |
| Experiments tab | ✅ Exists | No overlap |
| Recommendation Memory tab | ✅ Exists | No overlap |
| Ingestion Status tab | ✅ Exists | No overlap |
| Approvals tab | ✅ Exists | No overlap |

### Needs Migration (copy logic, adapt to Python)

| Component | Source | Complexity | Priority |
|-----------|--------|------------|----------|
| Daily Summary tab | dailySummary.js | Medium | HIGH |
| Daily Control tab | dailyControl.js | Medium | HIGH |
| Daily Input tab | managementWorkbook.js | High | HIGH |
| Daily SKU tab | dailySummary.js | Low | HIGH |
| PL History tab | dailySummary.js | Low | MEDIUM |
| Finance Raw tab | dailySummary.js | Low | MEDIUM |
| Orders Raw tab | dailySummary.js | Low | MEDIUM |
| PL Diagnostics tab | dailySummary.js | Low | MEDIUM |
| P&L Summary tab | reportBuilder.js | Medium | MEDIUM |
| SKU Dashboard tab | reportBuilder.js | High | MEDIUM |
| Products tab | jobs.js | Low | HIGH |
| Stocks tab | jobs.js | Low | HIGH |
| Alerts tab | alerts.js | Low | MEDIUM |
| COGS Mapping tab | manual | Low | HIGH |

### Needs Rewrite (different approach required)

| Component | Reason |
|-----------|--------|
| Performance Campaigns tab | Requires Performance API client (not yet in ozon-ai-agent) |
| Performance Stats tab | Requires Performance API CSV parser (not yet in ozon-ai-agent) |
| Ads Budget Plan tab | Requires ads optimizer engine (Phase 2) |
| Replenishment Plan tab | Requires replenishment engine (Phase 2) |
| Monthly sheet cloning | Daily Input uses template clone — need gspread equivalent |

### Can Be Removed

| Component | Reason |
|-----------|--------|
| Apps Script webhook approach | ozon-ai-agent uses gspread directly — better |
| Freeform `/sheet` command | Security risk — any user can write to any tab |
| Highlight.js / Marked.js dependencies | Not used in ollama-bot source |

---

## 6. Key Differences Between Approaches

| Aspect | ollama-bot | ozon-ai-agent |
|--------|-----------|---------------|
| **API** | Apps Script webhook (HTTP POST) | gspread direct API |
| **Auth** | Webapp URL (no credentials in bot) | Service account JSON |
| **Rate limiting** | Chunked writes (100 rows) | Throttled sync (10s delay) |
| **Fallback** | None (webapp must be up) | File-based fallback |
| **Formatting** | Apps Script handles formatting | gspread-formatting library |
| **Monthly tabs** | Template cloning (createMonthlySheet) | Not yet implemented |
| **Error handling** | Retry with backoff | Retry with exponential backoff |

---

## 7. Migration Priority

### Phase 1 (Week 1-2): Core Daily Operations

| Tab | Why First |
|-----|-----------|
| Products | Foundation for all other tabs |
| Stocks | Foundation for replenishment/alerts |
| Daily Summary | Core daily visibility |
| Daily Control | Operational plan vs actual |
| Daily Input | Management workbook (monthly) |
| Daily SKU | Per-SKU breakdown |
| Alerts | Monitoring |

### Phase 2 (Week 3-4): Analytics & Reports

| Tab | Why Later |
|-----|-----------|
| P&L Summary | Needs daily P&L data first |
| SKU Dashboard | Needs performance + sales data |
| Finance Raw | Audit trail (nice to have) |
| Orders Raw | Audit trail (nice to have) |
| PL History | Historical tracking |
| PL Diagnostics | Debug metadata |
| COGS Mapping | COGS management UI |

### Phase 3 (Week 5+): Advanced Features

| Tab | Why Last |
|-----|----------|
| Performance Campaigns | Requires Performance API client |
| Performance Stats | Requires Performance API CSV parser |
| Ads Budget Plan | Requires ads optimizer |
| Replenishment Plan | Requires replenishment engine |
