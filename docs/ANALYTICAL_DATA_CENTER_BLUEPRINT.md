# Analytical Data Center Blueprint

## Part 1: Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Ozon Seller  │ Ozon Perf.   │ Historical   │ Market / Competitor│
│ API          │ API          │ Files        │ Data               │
│              │              │              │                    │
│ products     │ campaigns    │ CSV exports  │ product pages      │
│ stocks       │ stats reports│ Excel sheets │ search results     │
│ orders FBO   │ campaign obj │ old JSON     │ Firecrawl          │
│ orders FBS   │ limits       │ old Sheets   │ manual snapshots   │
│ finance      │              │              │                    │
│ returns      │              │              │                    │
│ reviews      │              │              │                    │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAW DATA LAKE                                 │
│                                                                  │
│   data/raw/              data/raw/           data/raw/          │
│   seller_api/            performance/        market/            │
│   ├─ products.json       ├─ campaigns.json   ├─ snapshots/      │
│   ├─ stocks.json         ├─ stats.csv        ├─ search/         │
│   ├─ orders.json         └─ reports/         └─ firecrawl/      │
│   ├─ finance.json                                                 │
│   └─ reviews.json                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 NORMALIZED STORAGE                               │
│                                                                  │
│   src/ozon_agent/ingestion/                                     │
│   ├─ normalizers.py     (field mapping, dedup)                  │
│   ├─ validators.py      (schema validation)                     │
│   └─ store.py           (write to DB or files)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              POSTGRESQL DATA WAREHOUSE                           │
│                                                                  │
│   Core Tables:                                                   │
│   products, stocks, orders, finance_transactions, sales          │
│   advertising, performance_campaigns, performance_stats          │
│                                                                  │
│   P&L Tables:                                                    │
│   daily_pnl, daily_sku_pnl, daily_control, cogs                 │
│                                                                  │
│   Learning Tables:                                               │
│   recommendations, recommendation_outcomes, experiments          │
│   experiment_events, retro_patterns                              │
│                                                                  │
│   Knowledge Tables:                                              │
│   knowledge_articles, competitor_snapshots                       │
│                                                                  │
│   System Tables:                                                 │
│   etl_log, alerts, schema_migrations                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ANALYTICS ENGINES                              │
│                                                                  │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│   │ Daily P&L   │ │ Ads         │ │ SKU         │              │
│   │ Engine      │ │ Diagnostics │ │ Performance │              │
│   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘              │
│          │               │               │                      │
│   ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐              │
│   │ Stock &     │ │ Search /    │ │ Competitor  │              │
│   │ Replenish   │ │ SEO Engine  │ │ Engine      │              │
│   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘              │
│          │               │               │                      │
│   ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐              │
│   │ Retro       │ │ Forecasting │ │ Knowledge   │              │
│   │ Pattern     │ │ Engine      │ │ Agent       │              │
│   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘              │
│          │               │               │                      │
│          └───────────────┼───────────────┘                      │
│                          ▼                                      │
│   ┌─────────────────────────────────────┐                       │
│   │       DECISION / LEARNING LAYER     │                       │
│   │                                     │                       │
│   │  Recommendation Engine             │                       │
│   │  Confidence Calibration            │                       │
│   │  Outcome Tracking                  │                       │
│   │  Memory Update                     │                       │
│   └──────────────┬──────────────────────┘                       │
│                  │                                              │
└──────────────────┼──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   USER INTERFACE                                 │
│                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │  Telegram    │  │  Google      │  │  CLI         │         │
│   │  Bot         │  │  Sheets      │  │  Interface   │         │
│   │              │  │              │  │              │         │
│   │  /daily      │  │  Dashboard   │  │  analyze     │         │
│   │  /ads        │  │  Daily Sum.  │  │  forecast    │         │
│   │  /sku        │  │  Daily Ctrl  │  │  recommend   │         │
│   │  /alerts     │  │  Performance │  │  experiment  │         │
│   │  /pnl        │  │  Products    │  │  learn       │         │
│   │  /recommend  │  │  Stocks      │  │  sheets sync │         │
│   │  /retro      │  │  Alerts      │  │              │         │
│   │  /learn      │  │  Recs        │  │              │         │
│   │  /status     │  │  ...14 tabs  │  │              │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Data Sources

### Ozon Seller API

| Endpoint | Method | Data | Frequency | Priority |
|----------|--------|------|-----------|----------|
| `/v2/product/list` | POST | Product catalog | Daily | HIGH |
| `/v2/product/info/list` | POST | Product details | Daily | HIGH |
| `/v4/product/info/stocks` | POST | Stock levels | Daily | HIGH |
| `/v3/posting/fbo/list` | POST | FBO orders | Daily | HIGH |
| `/v3/posting/fbs/list` | POST | FBS orders | Daily | HIGH |
| `/v3/finance/transaction/list` | POST | Finance transactions | Daily | HIGH |
| `/v1/finance/realization` | POST | Finance orders | Daily | MEDIUM |
| `/v1/review/list` | POST | Reviews | Daily | MEDIUM |
| `/v1/product/info/stocks-by-warehouse/fbs` | POST | FBS stock details | Weekly | LOW |

### Ozon Performance API

| Endpoint | Method | Data | Frequency | Priority |
|----------|--------|------|-----------|----------|
| `/api/client/token` | POST | OAuth token | On-demand | HIGH |
| `/api/client/campaign` | GET | Campaign list | Weekly | HIGH |
| `/api/client/campaign/:id/objects` | GET | Campaign objects | Weekly | MEDIUM |
| `/api/client/statistics` | POST | Create stats report | Daily | HIGH |
| `/api/client/statistics/list` | GET | Report status | Daily | HIGH |
| `/api/client/statistics/report` | GET | Download CSV | Daily | HIGH |
| `/api/client/limits/list` | GET | Bid limits | Weekly | LOW |
| `/api/client/min/sku` | POST | Min bid per SKU | Weekly | LOW |

### Historical Files

| Source | Format | Content | Import Method |
|--------|--------|---------|---------------|
| CSV exports | CSV | P&L data, sales history | `ingestion/csv_importer.py` |
| Excel sheets | XLSX | Management workbook | `ingestion/excel_importer.py` |
| ollama-bot JSON | JSON | Sales, finance, performance | `ingestion/json_importer.py` |
| Old Google Sheets | Apps Script | Historical data | Export → CSV → import |

### Market / Competitor Data

| Source | Method | Data | Frequency |
|--------|--------|------|-----------|
| Product pages | Firecrawl | Competitor prices, descriptions | Weekly |
| Search results | Playwright/CDP | Search positions, competitors | Weekly |
| Manual snapshots | Telegram command | Market observations | On-demand |
| Category analytics | Ozon analytics | Market trends | Monthly |

### Ozon Knowledge Base

| Source | Content | Use |
|--------|---------|-----|
| Seller help | Platform rules, best practices | Recommendation context |
| Advertising docs | Campaign types, bidding | Ads recommendations |
| API docs | Endpoint schemas | Integration reference |
| Logistics docs | Delivery rules, costs | Cost optimization |

---

## Part 3: Data Warehouse Model

### Core Tables

#### `products`
```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    offer_id VARCHAR(255) NOT NULL,
    sku VARCHAR(255) NOT NULL,
    product_id BIGINT,
    name TEXT,
    category VARCHAR(500),
    brand VARCHAR(255),
    price NUMERIC(12,2),
    old_price NUMERIC(12,2),
    cost_price NUMERIC(12,2),
    weight_grams INT,
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(offer_id, sku)
);
```
- **Source:** Seller API `/v2/product/list`
- **Refresh:** Daily
- **Used by:** All engines

#### `product_daily_metrics`
```sql
CREATE TABLE product_daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    price NUMERIC(12,2),
    stock_total INT,
    orders INT DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    returns INT DEFAULT 0,
    ad_spend NUMERIC(12,2) DEFAULT 0,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    ctr NUMERIC(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, sku)
);
```
- **Source:** Aggregated from orders + sales + advertising
- **Refresh:** Daily
- **Used by:** SKU Performance, Daily P&L, Forecasting

#### `orders`
```sql
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    posting_number VARCHAR(255),
    product_id BIGINT REFERENCES products(id),
    offer_id VARCHAR(255),
    sku VARCHAR(255),
    quantity INT DEFAULT 1,
    price NUMERIC(12,2),
    final_price NUMERIC(12,2),
    status VARCHAR(100),
    scheme VARCHAR(10),
    region VARCHAR(255),
    city VARCHAR(255),
    created_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Seller API FBO/FBS
- **Refresh:** Daily
- **Used by:** Daily P&L, SKU Performance, Analytics

#### `finance_transactions`
```sql
CREATE TABLE finance_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    operation_type TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payout NUMERIC(12,2) DEFAULT 0,
    service_name TEXT,
    sku TEXT,
    offer_id TEXT,
    quantity INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Seller API `/v3/finance/transaction/list`
- **Refresh:** Daily
- **Used by:** Daily P&L, Economics

#### `stock_snapshots`
```sql
CREATE TABLE stock_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    warehouse TEXT,
    stock_total INT DEFAULT 0,
    stock_fbo INT DEFAULT 0,
    stock_fbs INT DEFAULT 0,
    in_transit INT DEFAULT 0,
    reserved INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Seller API `/v4/product/info/stocks`
- **Refresh:** Daily
- **Used by:** Stock & Replenishment, SKU Performance

#### `performance_campaigns`
```sql
CREATE TABLE performance_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id TEXT NOT NULL UNIQUE,
    name TEXT,
    state TEXT,
    campaign_type TEXT,
    budget NUMERIC(12,2),
    daily_budget NUMERIC(12,2),
    payment_type TEXT,
    placement TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Performance API `/api/client/campaign`
- **Refresh:** Weekly
- **Used by:** Ads Diagnostics

#### `performance_stats`
```sql
CREATE TABLE performance_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    campaign_id TEXT NOT NULL,
    campaign_name TEXT,
    sku TEXT,
    product_name TEXT,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    spend NUMERIC(12,2) DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Performance API CSV reports
- **Refresh:** Daily
- **Used by:** Ads Diagnostics, Daily P&L

### P&L Tables

#### `daily_pnl`
```sql
CREATE TABLE daily_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE UNIQUE NOT NULL,
    revenue NUMERIC(12,2) DEFAULT 0,
    returns NUMERIC(12,2) DEFAULT 0,
    orders_count INTEGER DEFAULT 0,
    commission NUMERIC(12,2) DEFAULT 0,
    logistics NUMERIC(12,2) DEFAULT 0,
    partner_services NUMERIC(12,2) DEFAULT 0,
    fbo_services NUMERIC(12,2) DEFAULT 0,
    advertising NUMERIC(12,2) DEFAULT 0,
    cogs_total NUMERIC(12,2) DEFAULT 0,
    gross_profit NUMERIC(12,2) DEFAULT 0,
    margin_pct NUMERIC(6,2) DEFAULT 0,
    drr_pct NUMERIC(6,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Calculated from finance + orders + performance + cogs
- **Refresh:** Daily
- **Used by:** Daily P&L Engine, Alerts, Forecasting

#### `daily_sku_pnl`
```sql
CREATE TABLE daily_sku_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    cogs NUMERIC(12,2) DEFAULT 0,
    ad_spend NUMERIC(12,2) DEFAULT 0,
    gross_profit NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, sku)
);
```
- **Source:** Calculated from postings + performance + cogs
- **Refresh:** Daily
- **Used by:** SKU Performance, Alerts

#### `daily_control`
```sql
CREATE TABLE daily_control (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE UNIQUE NOT NULL,
    orders INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    commission NUMERIC(12,2) DEFAULT 0,
    advertising NUMERIC(12,2) DEFAULT 0,
    cogs NUMERIC(12,2) DEFAULT 0,
    logistics NUMERIC(12,2) DEFAULT 0,
    gross_profit NUMERIC(12,2) DEFAULT 0,
    margin_pct NUMERIC(6,2) DEFAULT 0,
    plan_vp NUMERIC(12,2) DEFAULT 0,
    deviation NUMERIC(12,2) DEFAULT 0,
    cumulative_vp NUMERIC(12,2) DEFAULT 0,
    run_rate NUMERIC(12,2) DEFAULT 0,
    status TEXT DEFAULT 'NO DATA',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Calculated from daily_pnl + plan
- **Refresh:** Daily
- **Used by:** Daily Control, Alerts

#### `cogs`
```sql
CREATE TABLE cogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT NOT NULL UNIQUE,
    unit_cost NUMERIC(12,2) NOT NULL,
    logistics_cost NUMERIC(12,2) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** User input (Telegram)
- **Refresh:** Manual
- **Used by:** Daily P&L, SKU Performance

### Learning Tables

#### `recommendations`
```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY,
    sku TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence_score NUMERIC(8,4),
    confidence_level TEXT,
    risk_score NUMERIC(8,4),
    risk_level TEXT,
    expected_effect JSONB,
    status TEXT NOT NULL,
    approved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Decision Engine
- **Refresh:** On recommendation
- **Used by:** Recommendation Engine, Learning

#### `recommendation_outcomes`
```sql
CREATE TABLE recommendation_outcomes (
    id UUID PRIMARY KEY,
    recommendation_id UUID REFERENCES recommendations(id),
    observation_window_days INTEGER,
    expected_effect JSONB,
    actual_effect JSONB,
    forecast_error NUMERIC(8,4),
    success_score NUMERIC(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Outcome tracker
- **Refresh:** After observation window
- **Used by:** Learning Engine, Confidence Calibration

#### `experiments`
```sql
CREATE TABLE experiments (
    id UUID PRIMARY KEY,
    sku TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    baseline_orders NUMERIC(12,2) DEFAULT 0,
    baseline_revenue NUMERIC(12,2) DEFAULT 0,
    current_orders NUMERIC(12,2) DEFAULT 0,
    current_revenue NUMERIC(12,2) DEFAULT 0,
    success_score NUMERIC(8,4),
    direction_accuracy NUMERIC(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Experiment Engine
- **Refresh:** On experiment lifecycle
- **Used by:** Experiment Engine, Learning

#### `retro_patterns`
```sql
CREATE TABLE retro_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type TEXT NOT NULL,
    sku TEXT,
    trigger_signal TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    outcome TEXT NOT NULL,
    success_score NUMERIC(8,4),
    sample_size INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Retro Pattern Engine
- **Refresh:** After outcome evaluation
- **Used by:** Recommendation Engine, Learning

### Knowledge Tables

#### `knowledge_articles`
```sql
CREATE TABLE knowledge_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    relevance_score NUMERIC(4,3) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Ozon knowledge base, docs
- **Refresh:** Monthly
- **Used by:** Knowledge Agent, Recommendation context

#### `competitor_snapshots`
```sql
CREATE TABLE competitor_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    competitor_name TEXT,
    competitor_price NUMERIC(12,2),
    competitor_rating NUMERIC(3,2),
    competitor_reviews INT,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
- **Source:** Firecrawl, manual snapshots
- **Refresh:** Weekly
- **Used by:** Competitor Engine, Search/SEO Engine

### System Tables

#### `alerts`
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    metric_value NUMERIC(12,2),
    threshold NUMERIC(12,2),
    sku TEXT,
    signature TEXT NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `etl_log`
```sql
CREATE TABLE etl_log (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    rows_fetched INT DEFAULT 0,
    rows_inserted INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

---

## Part 4: Analytics Engines

### 1. Daily P&L Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | finance_transactions, postings, performance_stats, cogs |
| **Outputs** | daily_pnl, daily_sku_pnl, daily_control |
| **Signals** | margin < 20%, DRR > 25%, negative GP, plan deviation |
| **Telegram** | `/daily`, `/pnl`, `/daily control` |
| **Sheets** | Daily Summary, Daily Control, Daily Input |
| **Feedback** | Feeds into Decision Engine for cost optimization recommendations |

### 2. Ads Diagnostics Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | performance_stats, performance_campaigns, finance_transactions |
| **Outputs** | Campaign summaries, SKU ad metrics, reconciliation, gap analysis |
| **Signals** | High DRR, low CTR, spend without orders, low ROAS |
| **Telegram** | `/ads report`, `/ads reconcile`, `/ads factors`, `/ads campaigns` |
| **Sheets** | Performance Stats, Ads Budget Plan |
| **Feedback** | Feeds into Decision Engine for ad optimization recommendations |

### 3. SKU Performance Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | product_daily_metrics, stock_snapshots, performance_stats, cogs |
| **Outputs** | SKU rankings, margin analysis, sales velocity, stock days |
| **Signals** | Declining sales, low margin, high stock days, stockout risk |
| **Telegram** | `/sku <sku>`, `/sku top`, `/sku margin` |
| **Sheets** | SKU Dashboard, Products |
| **Feedback** | Feeds into Decision Engine for SKU-level recommendations |

### 4. Stock & Replenishment Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | stock_snapshots, product_daily_metrics, cogs |
| **Outputs** | Stock days, replenishment suggestions, OOS risk |
| **Signals** | Stock < 7 days, stockout probability > 0.6, in-transit monitoring |
| **Telegram** | `/stock`, `/stock low`, `/replenishment` |
| **Sheets** | Stocks, Replenishment Plan |
| **Feedback** | Feeds into Decision Engine for INCREASE_STOCK recommendations |

### 5. Search / SEO Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | search_positions (planned), products, competitors |
| **Outputs** | Search rankings, keyword analysis, title optimization |
| **Signals** | Ranking drop, low CTR by query, missing keywords |
| **Telegram** | `/search <query>`, `/seo <sku>` |
| **Sheets** | Search Rankings (planned) |
| **Feedback** | Feeds into Decision Engine for IMPROVE_CONTENT recommendations |

### 6. Competitor Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | competitor_snapshots, products |
| **Outputs** | Price comparisons, rating gaps, market positioning |
| **Signals** | Price above market, competitor price drop, rating gap |
| **Telegram** | `/competitors`, `/competitors <sku>` |
| **Sheets** | Competitors, Market Insights |
| **Feedback** | Feeds into Decision Engine for pricing recommendations |

### 7. Retro Pattern Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | recommendation_outcomes, experiments, retro_patterns |
| **Outputs** | Successful patterns, failed patterns, pattern confidence |
| **Signals** | Repeated success for same action/SKU, repeated failure |
| **Telegram** | `/retro <sku>`, `/retro patterns` |
| **Sheets** | Retro Cases (planned) |
| **Feedback** | Feeds into Recommendation Engine for pattern-based recommendations |

### 8. Recommendation Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | All engines' signals, knowledge articles, memory |
| **Outputs** | Ranked recommendations with confidence/risk |
| **Signals** | Composite opportunity score from all engines |
| **Telegram** | `/recommendations`, `/recommendations show <id>` |
| **Sheets** | Recommendations |
| **Feedback** | Outcomes tracked via approval workflow |

### 9. Learning / Outcome Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | recommendation_outcomes, retro_patterns, experiments |
| **Outputs** | Confidence calibration, success rates, pattern learning |
| **Signals** | Accuracy below threshold, calibration drift |
| **Telegram** | `/learn summary`, `/learn calibrate`, `/learn backtest` |
| **Sheets** | Learning Outcomes (planned) |
| **Feedback** | Updates confidence scores in Decision Engine |

### 10. Forecasting Engine

| Aspect | Details |
|--------|---------|
| **Inputs** | product_daily_metrics (historical), stock_snapshots |
| **Outputs** | Sales forecasts, stock predictions, ROI estimates |
| **Signals** | Forecast vs actual deviation, model accuracy |
| **Telegram** | `/forecast <sku>`, `/forecast stock` |
| **Sheets** | Forecast Dashboard (planned) |
| **Feedback** | Improves recommendation confidence |

---

## Part 5: User Interface Model

### Telegram Commands

| Command | What User Sees | Data Source | Action | Creates Outcome |
|---------|---------------|-------------|--------|-----------------|
| `/daily` | P&L summary: revenue, costs, GP, margin, DRR, status | daily_pnl | Read | No |
| `/daily YYYY-MM-DD` | P&L for specific date | daily_pnl | Read | No |
| `/pnl` | Full P&L breakdown with all cost categories | daily_pnl + finance_transactions | Read | No |
| `/ads` | Ads summary: spend, DRR, ROAS, top campaigns | performance_stats | Read | No |
| `/ads <sku>` | SKU-level ad performance | performance_stats | Read | No |
| `/sku <sku>` | Full SKU analysis: sales, margin, stock, ads | product_daily_metrics + stock_snapshots + performance_stats | Read | No |
| `/sku top` | Top 10 SKUs by revenue | product_daily_metrics | Read | No |
| `/alerts` | Active alerts: low margin, high DRR, low stock | alerts | Read | No |
| `/alerts acknowledge <id>` | Acknowledge alert | alerts | Write | No |
| `/stock` | Stock overview: days of stock, OOS risk | stock_snapshots | Read | No |
| `/stock low` | SKUs with stock < 7 days | stock_snapshots | Read | No |
| `/recommendations` | List pending recommendations | recommendations | Read | No |
| `/recommendations show <id>` | Recommendation details | recommendations | Read | No |
| `/recommendations approve <id>` | Approve recommendation | recommendations | Write | Yes |
| `/recommendations reject <id> <reason>` | Reject recommendation | recommendations | Write | No |
| `/why_down <sku>` | Root cause analysis for declining SKU | product_daily_metrics + performance_stats + stock_snapshots | Read | No |
| `/retro <sku>` | Retro cases for SKU | retro_patterns | Read | No |
| `/retro patterns` | All successful patterns | retro_patterns | Read | No |
| `/learn` | Learning summary: accuracy, calibration | recommendation_outcomes | Read | No |
| `/learn summary` | Detailed learning metrics | recommendation_outcomes | Read | No |
| `/status` | System health: DB, APIs, Sheets, last sync | etl_log + sheets sync status | Read | No |

### Google Sheets Tabs

#### MVP Tabs (Phase A-C)

| Tab | Columns | Mode | Data Source |
|-----|---------|------|-------------|
| **Dashboard** | Key metrics: revenue, GP, margin, DRR, alerts count, recommendations count | replace | Aggregated |
| **Daily Summary** | Date, Revenue, Payout, Orders, Commission, Logistics, Advertising, COGS, Profit, Margin, DRR | append | daily_pnl |
| **Daily Control** | Date, Day, Orders, Revenue, Ads, COGS, Logistics, GP, Margin, Plan, Deviation, Cum VP, Run Rate, Status | replace | daily_control |
| **Products** | Name, SKU, Offer ID, Price, Stock | replace | products + stocks |
| **Stocks** | Name, SKU, Offer ID, Stock, Stock Days | replace | stock_snapshots |
| **Performance Stats** | Date, Campaign ID, SKU, Impressions, Clicks, CTR, Spend, Orders, Revenue, DRR | replace | performance_stats |
| **Ads Diagnostics** | SKU, Campaign, Spend, CTR, CPC, Orders, Revenue, DRR, ROAS, Status | replace | performance_stats |
| **Alerts** | Date, Severity, Type, Message, SKU, Acknowledged | append | alerts |
| **Recommendations** | ID, Status, SKU, Action, Confidence, Risk, Reason, Created | replace | recommendations |

#### Advanced Tabs (Phase D-F)

| Tab | Columns | Mode | Data Source |
|-----|---------|------|-------------|
| **SKU Dashboard** | SKU, Revenue, Orders, Margin, Stock Days, DRR, Ad Spend, Status | replace | product_daily_metrics |
| **P&L History** | Date, Revenue, Commission, Logistics, Ads, COGS, GP, Margin | append | daily_pnl |
| **Unit Economics** | SKU, Revenue, COGS, Commission, Logistics, Ads, GP, Margin % | replace | daily_sku_pnl + cogs |
| **Replenishment Plan** | SKU, Stock, Stock Days, Target, Recommended, Priority | replace | stock_snapshots + product_daily_metrics |
| **Retro Cases** | SKU, Pattern, Action, Outcome, Success Score, Sample Size | replace | retro_patterns |
| **Learning Outcomes** | Recommendation ID, SKU, Action, Expected, Actual, Success | append | recommendation_outcomes |
| **Competitors** | SKU, Competitor, Price, Rating, Reviews, Date | replace | competitor_snapshots |
| **Knowledge Rules** | Category, Rule, Signal, Action, Source | replace | knowledge_articles |

---

## Part 6: Learning Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEARNING LOOP                                 │
│                                                                  │
│   1. SIGNAL                                                      │
│      Opportunity detector scans features → produces Opportunity  │
│      Types: STOCK_RISK, AD_GROWTH, AD_WASTE, PRICE_*, RANKING_* │
│                                                                  │
│   2. HYPOTHESIS                                                  │
│      Knowledge engine provides context → Confidence engine scores│
│      Risk engine evaluates risk → Recommendation generated       │
│                                                                  │
│   3. RECOMMENDATION                                              │
│      Stored as PENDING → User reviews in Telegram               │
│      User: approve / reject with reason                          │
│                                                                  │
│   4. USER ACTION                                                 │
│      Approved → marked EXECUTED (manual or future auto)          │
│      Rejected → marked REJECTED with reason                      │
│                                                                  │
│   5. OUTCOME CHECK (3 / 7 / 14 days)                            │
│      Baseline snapshot taken at action time                      │
│      Current metrics compared after observation window           │
│      Success score: (actual - expected) / expected               │
│      Direction accuracy: correct / total directions              │
│                                                                  │
│   6. CONFIDENCE UPDATE                                           │
│      Calibration by action type, SKU, risk level                 │
│      Overconfident → reduce factor                               │
│      Underconfident → increase factor                            │
│                                                                  │
│   7. MEMORY UPDATE                                               │
│      Successful patterns → retro_patterns table                  │
│      Failed patterns → retro_patterns (marked as failed)         │
│      Recommendation memory updated with similar cases            │
│                                                                  │
│   8. FEEDBACK TO SIGNAL                                          │
│      Updated confidence → better recommendations                 │
│      Retro patterns → pattern-based recommendations              │
│      Failed patterns → avoid repeating                           │
└─────────────────────────────────────────────────────────────────┘
```

### Outcome Metrics

| Metric | Formula | Target | Used For |
|--------|---------|--------|----------|
| Success score | (actual_delta - expected_delta) / expected_delta | > 0.5 | Overall success |
| Direction accuracy | correct_directions / total_directions | > 0.6 | Trend prediction |
| Revenue impact | (current_revenue - baseline_revenue) / baseline | > 0% | Revenue optimization |
| Margin impact | current_margin - baseline_margin | > 0 p.p. | Cost optimization |
| DRR impact | baseline_drr - current_drr | > 0 p.p. | Ad efficiency |
| Stock impact | maintained_stock_days >= target | True | Availability |

### Confidence Logic

```
base_confidence = feature_freshness * sample_size_factor * forecast_factor

calibration_factor = historical_success_rate / overall_success_rate

adjusted_confidence = base_confidence * calibration_factor

If adjusted_confidence > 1.0: cap at 0.95
If adjusted_confidence < 0.1: floor at 0.1
```

### Avoiding Failed Recommendations

```python
# In recommendation_engine.py
if pattern_exists_in_retro(action, sku, outcome="FAILED"):
    confidence *= 0.5  # Reduce confidence for known failures
    reason += f" [History: {pattern.sample_size} failures]"

if pattern_exists_in_retro(action, sku, outcome="SUCCESS"):
    confidence *= 1.2  # Boost confidence for known successes
    confidence = min(confidence, 0.95)
    reason += f" [History: {pattern.sample_size} successes]"
```

---

## Part 7: Implementation Phases

### Phase A — Data Foundation (Week 1-2)

| Task | Effort | Output |
|------|--------|--------|
| Stable Seller API ingestion | 2 days | products, stocks, orders, finance in DB |
| Stable Performance API ingestion | 2 days | campaigns, stats in DB |
| Raw + normalized storage | 1 day | data/raw/ structure |
| Sheets: Products, Stocks tabs | 1 day | 2 tabs live |

### Phase B — Daily P&L (Week 3-4)

| Task | Effort | Output |
|------|--------|--------|
| COGS management | 1 day | cogs table + Telegram commands |
| Finance transaction ingestion | 1 day | finance_transactions table |
| Orders ingestion (FBO/FBS) | 1 day | postings data |
| daily_pnl calculation | 1 day | daily_pnl + daily_sku_pnl tables |
| daily_control calculation | 1 day | daily_control table |
| Sheets: Daily Summary, Daily Control, Daily Input | 1 day | 3 tabs live |
| Telegram: /daily, /pnl | 1 day | Commands live |

### Phase C — Ads Intelligence (Week 5-6)

| Task | Effort | Output |
|------|--------|--------|
| Performance Stats ingestion | 2 days | performance_stats populated |
| Ads Diagnostics engine | 2 days | Campaign + SKU analysis |
| Reconciliation (Performance vs Finance) | 1 day | Gap detection |
| Alerts engine (DRR, spend, stock) | 1 day | alerts table + notifications |
| Sheets: Performance Stats, Ads Diagnostics, Alerts | 1 day | 3 tabs live |
| Telegram: /ads, /alerts | 1 day | Commands live |

### Phase D — SKU Intelligence (Week 7-8)

| Task | Effort | Output |
|------|--------|--------|
| product_daily_metrics aggregation | 1 day | Daily SKU metrics |
| Stock snapshots ingestion | 1 day | Daily stock tracking |
| SKU Performance engine | 2 days | Rankings, margin, velocity |
| Sheets: SKU Dashboard, Unit Economics | 1 day | 2 tabs live |
| Telegram: /sku, /why_down, /stock | 1 day | Commands live |

### Phase E — Learning (Week 9-10)

| Task | Effort | Output |
|------|--------|--------|
| Outcome tracking system | 2 days | recommendation_outcomes populated |
| Retro pattern engine | 2 days | retro_patterns table |
| Confidence calibration | 1 day | Calibration logic |
| Sheets: Retro Cases, Learning Outcomes | 1 day | 2 tabs live |
| Telegram: /retro, /learn | 1 day | Commands live |

### Phase F — Knowledge Agent (Week 11-12)

| Task | Effort | Output |
|------|--------|--------|
| Knowledge base ingestion | 2 days | knowledge_articles populated |
| Source-backed recommendations | 2 days | Recommendations cite knowledge |
| Algorithm hypotheses mapping | 1 day | Signals mapped to hypotheses |
| Sheets: Knowledge Rules | 1 tab | Tab live |
| Telegram: /why_down with knowledge context | 1 day | Enhanced analysis |

---

## Part 8: Rules

### System Rules

1. **Read-only by default** — No Ozon mutations without explicit approval
2. **No secrets in logs** — Never print API keys, tokens, or service account JSON
3. **No algorithm claims** — Always distinguish fact / hypothesis / recommendation
4. **Log all recommendations** — Every recommendation stored with full context
5. **Require outcome tracking** — Every approved recommendation must have outcome check
6. **Deduplication** — Alert signatures prevent duplicate notifications
7. **Graceful degradation** — File-based fallback when DB unavailable
8. **Rate limiting** — Respect API quotas, retry with backoff
9. **Audit trail** — All data mutations logged in etl_log
10. **User control** — User approves all significant actions

### Data Quality Rules

1. **Schema validation** — All ingested data validated against schema
2. **Deduplication** — UPSERT for daily metrics, UNIQUE constraints
3. **Null handling** — COALESCE for all numeric aggregations
4. **Date consistency** — All dates in UTC, displayed in user timezone
5. **Freshness tracking** — etl_log records data freshness

---

## Part 9: Roadmap

### MVP Definition

**What works after MVP:**
- Products and Stocks visible in Google Sheets
- Performance Stats synced daily
- 14 tabs in Google Sheets with real data
- Telegram: /daily, /ads, /sku, /alerts, /recommendations, /status
- Daily P&L calculated and displayed
- Basic ads diagnostics
- Basic alerts (low margin, high DRR, low stock)

### 30-Day Roadmap

| Day | Milestone |
|-----|-----------|
| 1-5 | Phase A: Seller API ingestion stable, Products/Stocks tabs |
| 6-10 | Phase A: Performance API ingestion stable, Performance Stats tab |
| 11-15 | Phase B: COGS, finance, orders ingestion |
| 16-20 | Phase B: daily_pnl, daily_control, Daily Summary/Control/Input tabs |
| 21-25 | Phase C: Ads Diagnostics, Alerts engine |
| 26-30 | Phase C: Performance Stats, Ads Diagnostics, Alerts tabs |

### 60-Day Roadmap

| Day | Milestone |
|-----|-----------|
| 31-35 | Phase D: product_daily_metrics, stock_snapshots |
| 36-40 | Phase D: SKU Performance engine, SKU Dashboard tab |
| 41-45 | Phase E: Outcome tracking, retro patterns |
| 46-50 | Phase E: Confidence calibration, Learning tabs |
| 51-55 | Phase F: Knowledge base ingestion |
| 56-60 | Phase F: Source-backed recommendations |

### 90-Day Roadmap

| Day | Milestone |
|-----|-----------|
| 61-70 | Search/SEO engine, competitor engine |
| 71-80 | Advanced forecasting, retro pattern learning |
| 81-90 | Full learning loop operational, all 14+ tabs live |

### Top 10 Highest Leverage Tasks

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 1 | COGS management (Telegram + DB) | Enables accurate P&L | 1 day |
| 2 | daily_pnl calculation engine | Core financial visibility | 2 days |
| 3 | Alerts engine (5 rules) | Proactive monitoring | 1 day |
| 4 | Performance Stats ingestion | Ad visibility | 2 days |
| 5 | SKU Daily Metrics aggregation | SKU-level analysis | 1 day |
| 6 | Outcome tracking system | Learning foundation | 2 days |
| 7 | Dashboard tab (aggregated view) | Single-glance status | 1 day |
| 8 | /why_down command | Root cause analysis | 1 day |
| 9 | Retro pattern engine | Pattern reuse | 2 days |
| 10 | Knowledge base ingestion | Source-backed recommendations | 2 days |

### What User Sees After Each Phase

| Phase | Telegram | Google Sheets |
|-------|----------|---------------|
| **A** | /status shows data freshness | Products, Stocks tabs with live data |
| **B** | /daily shows P&L, /pnl shows breakdown | Daily Summary, Daily Control, Daily Input tabs |
| **C** | /ads shows diagnostics, /alerts shows warnings | Performance Stats, Ads Diagnostics, Alerts tabs |
| **D** | /sku shows analysis, /why_down shows root cause | SKU Dashboard, Unit Economics tabs |
| **E** | /retro shows patterns, /learn shows accuracy | Retro Cases, Learning Outcomes tabs |
| **F** | /why_down includes knowledge context | Knowledge Rules tab |
