# Daily P&L Engine — Implementation Plan

## Part 1: Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
├──────────────────────┬──────────────────────────────────┤
│   Seller API         │   Performance API                 │
│   ─────────────      │   ────────────────                │
│   /finance/transaction│   /api/client/campaign           │
│   /posting/fbo       │   /api/client/statistics (CSV)    │
│   /posting/fbs       │                                   │
│   /product/list      │                                   │
│   /product/info/stocks│                                  │
└──────────┬───────────┴──────────────┬───────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│              RAW STORAGE (PostgreSQL)                    │
│                                                          │
│   finance_transactions    performance_stats              │
│   postings                performance_campaigns          │
│   products (existing)     advertising (existing)         │
│   stocks (existing)       sales (existing)               │
│   cogs                    etl_log (existing)             │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              DAILY P&L ENGINE                            │
│                                                          │
│   daily_pnl.py ─── calculates daily P&L metrics          │
│   daily_control.py ── plan vs actual comparison          │
│   daily_sync.py ──── orchestrates fetch → calc → write   │
│   cogs.py ─────────── COGS management                    │
│   alerts.py ────────── threshold-based alerts            │
└────────┬──────────┬──────────┬──────────┬───────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
    │ Sheets │ │  TG    │ │   DB   │ │  Decision  │
    │  tabs  │ │ alerts │ │ history│ │  Engine    │
    └────────┘ └────────┘ └────────┘ └────────────┘
```

### Data Flow Per Day

```
1. FETCH (daily_sync.py)
   ├─ Seller API: finance transactions → finance_transactions table
   ├─ Seller API: FBO postings → postings table
   ├─ Seller API: FBS postings → postings table
   └─ Performance API: stats CSV → performance_stats table

2. CALCULATE (daily_pnl.py)
   ├─ Revenue = SUM(final_price) from postings
   ├─ Commission = SUM(amount) from finance WHERE type = commission
   ├─ Logistics = SUM(amount) from finance WHERE type = logistics
   ├─ Advertising = SUM(spend) from performance_stats
   ├─ COGS = SUM(unit_cost × qty) from cogs × postings
   ├─ Gross Profit = Revenue - Commission - Logistics - Advertising - COGS
   ├─ Margin = GP / Revenue × 100
   └─ DRR = Advertising / Revenue × 100

3. CONTROL (daily_control.py)
   ├─ Compare GP vs plan
   ├─ Calculate deviation
   ├─ Calculate run-rate
   └─ Determine status: OK / BELOW PLAN / NO DATA

4. WRITE
   ├─ PostgreSQL: daily_pnl, daily_sku_pnl tables
   ├─ Google Sheets: 3 new tabs (daily_summary, daily_control, daily_sku)
   └─ Telegram: daily report message

5. ALERT (alerts.py)
   ├─ Check thresholds
   ├─ Deduplicate
   └─ Send to Telegram if new alert
```

---

## Part 2: Module Structure

### `src/ozon_agent/analytics/daily_pnl.py`

| Aspect | Details |
|--------|---------|
| **Responsibility** | Calculate daily P&L from raw data |
| **Inputs** | PostgreSQL: finance_transactions, postings, performance_stats, cogs |
| **Outputs** | DailyPnlRecord dataclass, daily_pnl table rows |
| **Dependencies** | db/connection.py, analytics/cogs.py |

```python
@dataclass
class DailyPnlRecord:
    date: str
    revenue: float
    returns: float
    orders_count: int
    commission: float
    logistics: float
    partner_services: float
    fbo_services: float
    advertising: float
    cogs_total: float
    gross_profit: float
    margin_pct: float
    drr_pct: float

def calculate_daily_pnl(date: str) -> DailyPnlRecord:
    """Calculate P&L for a single date from DB."""

def calculate_daily_sku_pnl(date: str) -> list[dict]:
    """Calculate per-SKU breakdown for a date."""

def store_daily_pnl(record: DailyPnlRecord) -> None:
    """Write to daily_pnl table."""
```

### `src/ozon_agent/analytics/daily_control.py`

| Aspect | Details |
|--------|---------|
| **Responsibility** | Plan vs actual comparison, run-rate calculation |
| **Inputs** | daily_pnl record, plan_vp_per_day config |
| **Outputs** | DailyControlRecord, daily_control table rows |
| **Dependencies** | analytics/daily_pnl.py |

```python
@dataclass
class DailyControlRecord:
    date: str
    weekday: str
    orders: int
    revenue: float
    commission: float
    advertising: float
    cogs: float
    logistics: float
    gross_profit: float
    margin_pct: float
    plan_vp: float
    deviation: float
    cumulative_vp: float
    run_rate: float
    status: str  # OK / BELOW PLAN / NO DATA

def build_control_row(date: str, plan_vp: float) -> DailyControlRecord:
    """Build control row for a date."""

def calculate_run_rate(cumulative_vp: float, day: int, days_in_month: int) -> float:
    """Calculate monthly run-rate."""
```

### `src/ozon_agent/analytics/daily_sync.py`

| Aspect | Details |
|--------|---------|
| **Responsibility** | Orchestrate fetch → calculate → write |
| **Inputs** | Seller API, Performance API, config |
| **Outputs** | SyncResult, writes to DB + Sheets + Telegram |
| **Dependencies** | api/ozon_client.py, api/performance_client.py, analytics/daily_pnl.py, analytics/daily_control.py, sheets/ |

```python
@dataclass
class SyncResult:
    date: str
    revenue: float
    gross_profit: float
    margin_pct: float
    status: str
    rows_fetched: int
    errors: list[str]

def sync_daily(date: str, to_sheet: bool = True) -> SyncResult:
    """Full daily sync: fetch → calculate → write."""

def fetch_finance(date: str) -> int:
    """Fetch finance transactions from Seller API."""

def fetch_postings(date: str) -> int:
    """Fetch FBO/FBS postings from Seller API."""

def build_summary_text(result: SyncResult) -> str:
    """Format for Telegram."""
```

### `src/ozon_agent/analytics/cogs.py`

| Aspect | Details |
|--------|---------|
| **Responsibility** | COGS CRUD, import, resolution |
| **Inputs** | User input (Telegram), bulk import |
| **Outputs** | cogs table rows, COGS lookup |
| **Dependencies** | db/connection.py |

```python
@dataclass
class CogsEntry:
    sku: str
    offer_id: str | None
    unit_cost: float
    logistics_cost: float

def set_cogs(sku: str, unit_cost: float, logistics_cost: float = 0) -> CogsEntry:
    """Set COGS for a SKU."""

def get_cogs(sku: str) -> float | None:
    """Lookup unit cost by SKU."""

def list_cogs() -> list[CogsEntry]:
    """List all COGS entries."""

def import_cogs_bulk(text: str) -> int:
    """Import COGS from text (SKU COST format)."""

def clear_cogs() -> int:
    """Clear all COGS entries."""

def get_cogs_status() -> dict:
    """Count products with/without COGS."""
```

### `src/ozon_agent/analytics/alerts.py`

| Aspect | Details |
|--------|---------|
| **Responsibility** | Threshold-based alert detection, deduplication |
| **Inputs** | daily_pnl, performance_stats, stocks, products |
| **Outputs** | AlertEvent list, alert history |
| **Dependencies** | db/connection.py |

```python
@dataclass
class AlertEvent:
    id: str
    alert_type: str
    severity: str  # high / medium / low
    message: str
    metric_value: float
    threshold: float
    sku: str | None
    created_at: str
    acknowledged: bool

def check_alerts() -> list[AlertEvent]:
    """Run all alert rules, return new alerts."""

def check_low_margin(pnl: DailyPnlRecord) -> AlertEvent | None:
def check_high_drr(pnl: DailyPnlRecord) -> AlertEvent | None:
def check_no_sales(date: str) -> AlertEvent | None:
def check_low_stock() -> list[AlertEvent]:
def check_high_commission(pnl: DailyPnlRecord) -> AlertEvent | None:
def check_spend_without_orders() -> AlertEvent | None:

def deduplicate(alerts: list[AlertEvent]) -> list[AlertEvent]:
    """Remove alerts already sent (SHA-1 signature)."""

def store_alert(alert: AlertEvent) -> None:
    """Write to alerts table."""
```

---

## Part 3: Database Migrations

### Existing Tables (reuse)

| Table | Reuse for |
|-------|-----------|
| `products` | SKU catalog, cost_price for COGS |
| `sales` | Daily revenue by SKU |
| `advertising` | Ad spend by SKU |
| `finance` | Daily finance summary |
| `etl_log` | Sync status tracking |

### New Tables Required

```sql
-- 004_daily_pnl.sql

-- Сырые транзакции Finance API (детализация)
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
CREATE INDEX idx_finance_tx_date ON finance_transactions(date);

-- Сырые постинги (FBO/FBS)
CREATE TABLE postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    order_id TEXT NOT NULL,
    posting_number TEXT,
    sku TEXT NOT NULL,
    offer_id TEXT,
    product_name TEXT,
    quantity INTEGER NOT NULL,
    price NUMERIC(12,2) NOT NULL,
    final_price NUMERIC(12,2) NOT NULL,
    scheme TEXT NOT NULL,
    status TEXT,
    region TEXT,
    city TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_postings_date ON postings(date);
CREATE INDEX idx_postings_sku ON postings(sku);

-- Performance API statistics
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
CREATE INDEX idx_perf_stats_date ON performance_stats(date);
CREATE INDEX idx_perf_stats_sku ON performance_stats(sku);

-- COGS (себестоимость)
CREATE TABLE cogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT NOT NULL UNIQUE,
    offer_id TEXT,
    unit_cost NUMERIC(12,2) NOT NULL,
    logistics_cost NUMERIC(12,2) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Агрегированный дневной P&L
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

-- P&L по SKU за день
CREATE TABLE daily_sku_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    offer_id TEXT,
    product_name TEXT,
    quantity INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    cogs NUMERIC(12,2) DEFAULT 0,
    ad_spend NUMERIC(12,2) DEFAULT 0,
    gross_profit NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, sku)
);
CREATE INDEX idx_daily_sku_date ON daily_sku_pnl(date);

-- Контрольная таблица (план vs факт)
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

-- Алерты
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
CREATE INDEX idx_alerts_date ON alerts(created_at DESC);
CREATE INDEX idx_alerts_signature ON alerts(signature);
```

### Migration Order

```
001_initial_schema.sql     ✅ Exists
002_recommendations.sql    ✅ Exists
003_experiments.sql        ✅ Exists
004_daily_pnl.sql          ← NEW (Part 3)
```

---

## Part 4: COGS System

### Where COGS Lives

**PostgreSQL table `cogs`** — single source of truth.

```
cogs table:
  sku TEXT UNIQUE    — привязка к товару
  offer_id TEXT      — альтернативный ID
  unit_cost FLOAT    — себестоимость за единицу
  logistics_cost FLOAT — логистика за единицу
  updated_at TIMESTAMP
```

### Import Flow

```
1. Telegram: /cogs set SKU-001 350 50
   → cogs.py: set_cogs("SKU-001", 350, 50)
   → PostgreSQL: INSERT/UPDATE cogs table

2. Telegram: /cogs import text
   → User sends multiline: "SKU-001 350\nSKU-002 420\nSKU-003 280"
   → cogs.py: import_cogs_bulk(text)
   → PostgreSQL: batch INSERT

3. Telegram: /cogs list
   → cogs.py: list_cogs()
   → Format: table with SKU, unit_cost, logistics_cost

4. Telegram: /cogs status
   → cogs.py: get_cogs_status()
   → Shows: total SKUs, with COGS, without COGS
```

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/cogs` | Show COGS status |
| `/cogs list` | List all COGS entries |
| `/cogs set SKU COST [LOGISTICS]` | Set COGS for SKU |
| `/cogs import text` | Bulk import from multiline text |
| `/cogs clear` | Clear all COGS |
| `/cogs debug SKU` | Show COGS resolution for SKU |

### Google Sheets Workflow

COGS management is Telegram-only (no Sheets tab). Rationale:
- COGS changes rarely (monthly at most)
- Telegram provides immediate feedback
- Sheets is for read-heavy dashboards, not CRUD

---

## Part 5: Alerts Engine

### Alert Rules

| Alert | Formula | Threshold | Severity | Dedup |
|-------|---------|-----------|----------|-------|
| **Low Margin** | margin_pct < threshold | 20% | HIGH | Per-day signature |
| **High DRR** | drr_pct > threshold | 25% | MEDIUM | Per-day signature |
| **No Sales** | orders_count == 0 | — | HIGH | Per-day signature |
| **Low Stock** | stock < threshold per SKU | 5 units | MEDIUM | Per-SKU-daily signature |
| **High Commission** | commission / revenue > threshold | 25% | MEDIUM | Per-day signature |
| **Spend Without Orders** | ad_spend > 0 AND orders == 0 (per SKU) | — | HIGH | Per-SKU-daily signature |

### Dedup Strategy

```python
def signature(alert_type: str, date: str, sku: str | None = None) -> str:
    """SHA-1 of alert_type + date + sku."""
    key = f"{alert_type}:{date}:{sku or 'all'}"
    return hashlib.sha1(key.encode()).hexdigest()

def deduplicate(alerts: list[AlertEvent]) -> list[AlertEvent]:
    """Check signature against alerts table, return only new ones."""
    for alert in alerts:
        existing = check_signature(alert.signature)
        if not existing:
            yield alert
```

### Alert Flow

```
1. check_alerts() runs after daily_sync
2. For each rule: generate AlertEvent if threshold breached
3. Deduplicate against alerts table
4. New alerts → store in alerts table
5. New alerts → format and send to Telegram
6. Alert types: low_margin, high_drr, no_sales, low_stock, high_commission, spend_no_orders
```

---

## Part 6: Google Sheets Integration

### Current 8 Tabs (keep as-is)

| Tab | Status |
|-----|--------|
| Daily Report | ✅ Existing |
| Recommendations | ✅ Existing |
| Market Insights | ✅ Existing |
| Competitors | ✅ Existing |
| Experiments | ✅ Existing |
| Recommendation Memory | ✅ Existing |
| Ingestion Status | ✅ Existing |
| Approvals | ✅ Existing |

### Phase 1: +3 Tabs (MVP)

| Tab | Data | Why |
|-----|------|-----|
| **Daily Summary** | Revenue, commission, logistics, ads, COGS, GP, margin, DRR | Core P&L view |
| **Daily Control** | Plan vs actual, deviation, run-rate, status | Operational control |
| **Alerts** | Alert history with severity | Monitoring |

**Rationale:** 3 tabs give complete daily visibility without overload. Daily Summary is the primary dashboard. Daily Control is for operational decisions. Alerts for monitoring.

### Phase 2: +3 Tabs (Extended)

| Tab | Data | Why |
|-----|------|-----|
| **Daily SKU** | Per-SKU revenue, COGS, ad spend, GP | SKU-level analysis |
| **Finance Raw** | Raw finance transactions | Audit trail |
| **Performance Stats** | Raw performance data | Debug/analysis |

**Rationale:** These are detail/audit tabs. Needed for deep analysis but not for daily operations. Add when SKU-level analysis is required.

### Total After Phase 2: 14 Tabs

```
Phase 1 (11 tabs):
  Daily Report, Recommendations, Market Insights, Competitors,
  Experiments, Recommendation Memory, Ingestion Status, Approvals,
  Daily Summary, Daily Control, Alerts

Phase 2 (14 tabs):
  + Daily SKU, Finance Raw, Performance Stats
```

---

## Part 7: Telegram Integration

### MVP Commands (Phase 1)

| Command | Description |
|---------|-------------|
| `/daily` | P&L за вчера |
| `/daily YYYY-MM-DD` | P&L за дату |
| `/daily в таблицу` | Записать в Google Sheets |
| `/daily control` | Контрольная таблица |
| `/daily control YYYY-MM-DD` | Контроль за дату |
| `/cogs` | Статус COGS |
| `/cogs list` | Список COGS |
| `/cogs set SKU COST` | Установить COGS |
| `/cogs import text` | Импорт COGS |
| `/alerts` | История алертов |
| `/sheets sync` | Синхронизация Sheets |

**Total: 11 commands**

### Advanced Commands (Phase 2)

| Command | Description |
|---------|-------------|
| `/daily summary YYYY-MM-DD` | Детальная сводка |
| `/daily debug YYYY-MM-DD` | Сырые данные |
| `/daily raw YYYY-MM-DD` | Сырые транзакции |
| `/report pnl YYYY-MM-DD` | P&L отчёт |
| `/report pnl в таблицу` | Записать P&L |
| `/report sku YYYY-MM-DD` | Отчёт по SKU |
| `/report sku в таблицу` | Записать SKU |
| `/sales fetch YYYY-MM-DD` | Загрузить продажи |
| `/sales status` | Статус продаж |
| `/finance fetch YYYY-MM-DD` | Загрузить финансы |
| `/finance status` | Статус финансов |
| `/cogs debug SKU` | Диагностика COGS |
| `/cogs clear` | Очистить COGS |
| `/alerts acknowledge` | Подтвердить алерт |

**Total: 14 additional commands**

### Command Explosion Prevention

```
Правило: каждая команда должна решать конкретную задачу.

Хорошо:
  /daily          — показать P&L (1 действие)
  /cogs set X Y   — установить COGS (1 действие)

Плохо:
  /daily full detailed report with charts and everything
  /cogs advanced import with validation and rollback
```

---

## Part 8: Decision Engine Integration

### Signal Flow

```
Daily P&L Engine
    │
    ├─→ Decision Engine: "low margin" signal
    │   → Recommendation: DECREASE_PRICE or IMPROVE_CONTENT
    │
    ├─→ Decision Engine: "high DRR" signal
    │   → Recommendation: DECREASE_BUDGET or PAUSE_CAMPAIGN
    │
    ├─→ Decision Engine: "no sales" signal
    │   → Recommendation: BOOST_REVIEWS or IMPROVE_CONTENT
    │
    ├─→ Decision Engine: "low stock" signal
    │   → Recommendation: INCREASE_STOCK
    │
    └─→ Forecasting: historical P&L data
        → Prophet/XGBoost models
        → Revenue/profit forecasts
```

### Integration Points

| P&L Signal | Decision Engine Input | Recommendation |
|-----------|----------------------|----------------|
| margin_pct < 20% | `DecisionFeature.gross_margin_pct` | DECREASE_PRICE, IMPROVE_CONTENT |
| drr_pct > 25% | `DecisionFeature.drr` | DECREASE_BUDGET, PAUSE_CAMPAIGN |
| orders == 0 for 7 days | `DecisionFeature.sales_quantity` | BOOST_REVIEWS, IMPROVE_CONTENT |
| stock < 5 | `DecisionFeature.current_stock` | INCREASE_STOCK |
| commission / revenue > 25% | `DecisionFeature.supporting_metrics` | DECREASE_PRICE (negotiate) |

### Data Flow to Decision Engine

```python
# daily_pnl.py → store_daily_pnl() → PostgreSQL
# decision/feature_store.py → reads daily_pnl + sales + advertising → DecisionFeature
# decision/recommendation_engine.py → generates Recommendations
# approval/ → stores as PENDING for Telegram approval
```

---

## MVP Scope (1 Week)

### What Can Be Done

| Task | Effort | Dependency |
|------|--------|-----------|
| Migration 004 (all new tables) | 1 day | None |
| `daily_pnl.py` — calculate P&L from DB | 1 day | Migration |
| `daily_control.py` — plan vs actual | 0.5 day | daily_pnl.py |
| `daily_sync.py` — orchestrate fetch + calc | 1 day | daily_pnl.py, API clients |
| `cogs.py` — COGS CRUD | 0.5 day | Migration |
| Sheets: daily_summary + daily_control tabs | 1 day | daily_pnl.py |
| Telegram: `/daily`, `/cogs`, `/alerts` (6 commands) | 1 day | daily_pnl.py, cogs.py |

### What's NOT in MVP

- Performance API client (separate task)
- Alerts engine (needs Performance data first)
- Daily SKU tab (Phase 2)
- Advanced Telegram commands (Phase 2)
- Decision Engine integration (Phase 2)

---

## Phase 1 Scope (Weeks 1-2)

| Task | Effort | Week |
|------|--------|------|
| Migration 004 | 1 day | Week 1 |
| daily_pnl.py | 1 day | Week 1 |
| daily_control.py | 0.5 day | Week 1 |
| daily_sync.py | 1 day | Week 1 |
| cogs.py | 0.5 day | Week 1 |
| Sheets: 3 tabs | 1 day | Week 1 |
| Telegram: 11 MVP commands | 1 day | Week 1 |
| Alerts engine | 1 day | Week 2 |
| Sheets: alerts tab | 0.5 day | Week 2 |
| Telegram: alerts commands | 0.5 day | Week 2 |
| Integration tests | 1 day | Week 2 |
| **Total** | **~8 days** | |

---

## Phase 2 Scope (Weeks 3-4)

| Task | Effort |
|------|--------|
| Daily SKU tab + exporter | 1 day |
| Finance Raw tab + exporter | 0.5 day |
| Performance Stats tab + exporter | 0.5 day |
| Advanced Telegram commands (14) | 2 days |
| Decision Engine signal integration | 1 day |
| Forecasting integration | 1 day |
| **Total** | **~6 days** |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Performance API CSV parsing edge cases | MEDIUM | Test with real CSV output, handle malformed rows |
| COGS data quality (missing SKUs) | HIGH | Show coverage status, warn on missing COGS |
| Finance API pagination limits | MEDIUM | Use page_size=1000, loop while has_next |
| Telegram message length limits | LOW | Split long messages at 3500 chars |
| Rate limits on Sheets writes | LOW | Already throttled (10s between tabs) |
| Timezone handling (Moscow) | MEDIUM | Use zoneinfo, test DST transitions |
| Alert dedup false negatives | LOW | SHA-1 per day per SKU, generous thresholds |

---

## Estimated Effort

| Phase | Duration | Team |
|-------|----------|------|
| MVP | 1 week | 1 developer |
| Phase 1 | 2 weeks | 1 developer |
| Phase 2 | 2 weeks | 1 developer |
| **Total** | **~5 weeks** | |

---

## Recommended Next Implementation

**Start with Migration 004 + daily_pnl.py**

These two are the foundation. Everything else depends on them:
- daily_control.py needs daily_pnl.py
- daily_sync.py needs daily_pnl.py
- Sheets tabs need daily_pnl data
- Telegram commands need daily_pnl data
- Alerts need daily_pnl data

After migration + daily_pnl.py, build outward:
1. cogs.py (COGS is needed for accurate COGS calculation)
2. daily_sync.py (orchestration)
3. Sheets tabs (visual output)
4. Telegram commands (user interface)
5. daily_control.py (plan comparison)
6. Alerts (monitoring)
