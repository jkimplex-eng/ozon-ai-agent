# Migration 004 — Specification

## Status: Design Only — No Code

---

## 1. Current Schema Review

### Existing Tables (from 001 + 002 + 003)

| Table | PK | Key Fields | Reuse for 004 |
|-------|-----|-----------|---------------|
| `products` | BIGSERIAL | offer_id, sku, **cost_price** | ✅ COGS source |
| `sales` | BIGSERIAL | product_id FK, date, quantity, revenue | ✅ Revenue source |
| `advertising` | BIGSERIAL | campaign_id, product_id FK, date, spend | ✅ Ad spend source |
| `finance` | BIGSERIAL | date (UNIQUE), ozon_commission, logistics, advertising | ✅ Finance summary |
| `finance_items` | BIGSERIAL | finance_id FK, product_id FK | ✅ Per-SKU finance |
| `orders` | BIGSERIAL | order_id (UNIQUE), product_id FK, final_price, scheme | ✅ Order details |
| `stocks` | BIGSERIAL | product_id FK, stock_total | ✅ Stock levels |
| `experiments` | UUID | sku, hypothesis, status | — |
| `experiment_events` | UUID | experiment_id FK | — |
| `recommendations` | UUID | sku, action, status | — |
| `etl_log` | BIGSERIAL | source, status | ✅ Sync tracking |

### Existing Views

| View | What it does | Reuse |
|------|-------------|-------|
| `v_daily_pnl` | Joins products+sales+finance+finance_items for daily P&L | ⚠️ Partial — uses old COGS logic |
| `v_sku_performance` | Aggregates sales+advertising+reviews per SKU | ✅ |

### Existing `calculate_daily_pnl()` Function

Located in `analytics/metrics.py`. Works with DataFrames. Calculates:
- Revenue from sales
- Commission, logistics, partner_services, fbo_services from finance
- Advertising from advertising table
- COGS from products.cost_price × quantity
- Gross profit = revenue + returns - expenses

**Gap:** No dedicated tables for raw API data, COGS management, daily aggregates, control, or alerts.

---

## 2. Tables to Add

### 2.1 `finance_transactions` — Raw Finance API Data

**Purpose:** Store individual finance transactions from Seller API `/v3/finance/transaction/list`. Currently `finance` table stores daily aggregates only. This table stores every transaction line for audit and debugging.

```sql
CREATE TABLE IF NOT EXISTS finance_transactions (
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

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL | Transaction date |
| `operation_type` | TEXT | NOT NULL | Ozon operation type string |
| `amount` | NUMERIC(12,2) | NOT NULL | Transaction amount (negative for deductions) |
| `payout` | NUMERIC(12,2) | DEFAULT 0 | Payout amount |
| `service_name` | TEXT | NULLABLE | Service name from Ozon |
| `sku` | TEXT | NULLABLE | SKU if per-product transaction |
| `offer_id` | TEXT | NULLABLE | Offer ID if per-product |
| `quantity` | INTEGER | DEFAULT 1 | Quantity for per-product transactions |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:**
```sql
CREATE INDEX idx_finance_tx_date ON finance_transactions(date);
CREATE INDEX idx_finance_tx_type ON finance_transactions(operation_type);
CREATE INDEX idx_finance_tx_sku ON finance_transactions(sku) WHERE sku IS NOT NULL;
```

**Unique constraints:** None — duplicate transactions possible from re-fetches.

**Foreign keys:** None — raw data, not linked to products.

**Volume estimate:**
- Per day: 50-500 transactions (depending on order count)
- Per month: 1,500-15,000 rows
- Growth: linear with order volume
- Retention: 90 days recommended (partition by month)

---

### 2.2 `postings` — Raw FBO/FBS Postings

**Purpose:** Store individual posting items from Seller API `/v3/posting/fbo/list` and `/v3/posting/fbs/list`. Currently `orders` table has similar data but uses `order_id` as UNIQUE which may conflict with posting_number.

```sql
CREATE TABLE IF NOT EXISTS postings (
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
```

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL | Posting date |
| `order_id` | TEXT | NOT NULL | Ozon order ID |
| `posting_number` | TEXT | NULLABLE | Posting number |
| `sku` | TEXT | NOT NULL | Product SKU |
| `offer_id` | TEXT | NULLABLE | Offer ID |
| `product_name` | TEXT | NULLABLE | Product name |
| `quantity` | INTEGER | NOT NULL | Quantity ordered |
| `price` | NUMERIC(12,2) | NOT NULL | Original price |
| `final_price` | NUMERIC(12,2) | NOT NULL | Final price after discounts |
| `scheme` | TEXT | NOT NULL | 'FBO' or 'FBS' |
| `status` | TEXT | NULLABLE | Posting status |
| `region` | TEXT | NULLABLE | Delivery region |
| `city` | TEXT | NULLABLE | Delivery city |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:**
```sql
CREATE INDEX idx_postings_date ON postings(date);
CREATE INDEX idx_postings_sku ON postings(sku);
CREATE INDEX idx_postings_scheme ON postings(scheme);
```

**Unique constraints:** None — same posting can be fetched multiple times.

**Foreign keys:** None — raw API data. SKU resolved separately via products table.

**Volume estimate:**
- Per day: 20-200 postings
- Per month: 600-6,000 rows
- Growth: linear with order volume
- Retention: 90 days recommended

---

### 2.3 `performance_campaigns` — Performance API Campaigns

**Purpose:** Store campaign metadata from Performance API `/api/client/campaign`. The `advertising` table already stores per-SKU stats but not campaign-level metadata.

```sql
CREATE TABLE IF NOT EXISTS performance_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id TEXT NOT NULL,
    name TEXT,
    state TEXT,
    campaign_type TEXT,
    budget NUMERIC(12,2),
    daily_budget NUMERIC(12,2),
    payment_type TEXT,
    placement TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id)
);
```

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `campaign_id` | TEXT | NOT NULL | Ozon Performance campaign ID |
| `name` | TEXT | NULLABLE | Campaign name |
| `state` | TEXT | NULLABLE | RUNNING, PAUSED, etc. |
| `campaign_type` | TEXT | NULLABLE | SEARCH, PROMO, etc. |
| `budget` | NUMERIC(12,2) | NULLABLE | Total budget |
| `daily_budget` | NUMERIC(12,2) | NULLABLE | Daily budget |
| `payment_type` | TEXT | NULLABLE | CPC, CPM, etc. |
| `placement` | TEXT | NULLABLE | Search, Promo, etc. |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | First seen |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last updated |

**Indexes:**
```sql
CREATE INDEX idx_perf_campaigns_state ON performance_campaigns(state);
```

**Unique constraints:** `campaign_id` UNIQUE — one row per campaign, updated on re-fetch.

**Foreign keys:** None — reference data.

**Volume estimate:**
- Static: 100-500 campaigns (depends on seller)
- Growth: minimal (new campaigns rare)
- Retention: indefinite

---

### 2.4 `performance_stats` — Performance API Statistics

**Purpose:** Store daily statistics from Performance API CSV reports. The `advertising` table already has similar data but is populated from a different source. This table stores the raw CSV-parsed data for audit.

```sql
CREATE TABLE IF NOT EXISTS performance_stats (
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

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL | Statistics date |
| `campaign_id` | TEXT | NOT NULL | Campaign ID |
| `campaign_name` | TEXT | NULLABLE | Campaign name |
| `sku` | TEXT | NULLABLE | Product SKU |
| `product_name` | TEXT | NULLABLE | Product name |
| `impressions` | INTEGER | DEFAULT 0 | Ad impressions |
| `clicks` | INTEGER | DEFAULT 0 | Ad clicks |
| `spend` | NUMERIC(12,2) | DEFAULT 0 | Ad spend |
| `orders` | INTEGER | DEFAULT 0 | Orders from ads |
| `revenue` | NUMERIC(12,2) | DEFAULT 0 | Revenue from ads |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:**
```sql
CREATE INDEX idx_perf_stats_date ON performance_stats(date);
CREATE INDEX idx_perf_stats_sku ON performance_stats(sku);
CREATE INDEX idx_perf_stats_campaign ON performance_stats(campaign_id);
```

**Unique constraints:** None — CSV reports can overlap.

**Foreign keys:** None — raw CSV data.

**Volume estimate:**
- Per day: 50-500 rows (campaign × SKU combinations)
- Per month: 1,500-15,000 rows
- Growth: linear with campaign count
- Retention: 90 days recommended

---

### 2.5 `cogs` — Cost of Goods Sold

**Purpose:** Store per-SKU cost of goods sold. Currently `products.cost_price` is used but it's a single value per product. This table allows logistics cost per SKU and historical tracking.

```sql
CREATE TABLE IF NOT EXISTS cogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT NOT NULL,
    offer_id TEXT,
    unit_cost NUMERIC(12,2) NOT NULL,
    logistics_cost NUMERIC(12,2) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sku)
);
```

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `sku` | TEXT | NOT NULL | Product SKU (UNIQUE) |
| `offer_id` | TEXT | NULLABLE | Offer ID (alternative lookup) |
| `unit_cost` | NUMERIC(12,2) | NOT NULL | Cost per unit |
| `logistics_cost` | NUMERIC(12,2) | DEFAULT 0 | Logistics cost per unit |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last updated |

**Indexes:** None needed — small table, UNIQUE on SKU.

**Unique constraints:** `sku` UNIQUE — one COGS entry per SKU.

**Foreign keys:** None — independent reference data.

**Volume estimate:**
- Static: 50-500 rows (one per SKU)
- Growth: minimal (new SKUs rare)
- Retention: indefinite

---

### 2.6 `daily_pnl` — Aggregated Daily P&L

**Purpose:** Store calculated daily P&L metrics. Pre-computed for fast reads in Sheets and Telegram.

```sql
CREATE TABLE IF NOT EXISTS daily_pnl (
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

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL, UNIQUE | One row per day |
| `revenue` | NUMERIC(12,2) | DEFAULT 0 | Total revenue |
| `returns` | NUMERIC(12,2) | DEFAULT 0 | Returns amount |
| `orders_count` | INTEGER | DEFAULT 0 | Number of orders |
| `commission` | NUMERIC(12,2) | DEFAULT 0 | Ozon commission |
| `logistics` | NUMERIC(12,2) | DEFAULT 0 | Logistics costs |
| `partner_services` | NUMERIC(12,2) | DEFAULT 0 | Partner services |
| `fbo_services` | NUMERIC(12,2) | DEFAULT 0 | FBO services |
| `advertising` | NUMERIC(12,2) | DEFAULT 0 | Ad spend |
| `cogs_total` | NUMERIC(12,2) | DEFAULT 0 | Total COGS |
| `gross_profit` | NUMERIC(12,2) | DEFAULT 0 | Gross profit |
| `margin_pct` | NUMERIC(6,2) | DEFAULT 0 | Margin percentage |
| `drr_pct` | NUMERIC(6,2) | DEFAULT 0 | DRR percentage |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:** None needed — UNIQUE on date, small table.

**Unique constraints:** `date` UNIQUE — one P&L per day.

**Foreign keys:** None — aggregated data.

**Volume estimate:**
- Static: 1 row per day
- Per year: 365 rows
- Growth: +1 row/day
- Retention: indefinite (small)

---

### 2.7 `daily_sku_pnl` — Per-SKU Daily P&L

**Purpose:** Store per-SKU breakdown for daily P&L. Used for SKU-level analysis and Daily SKU tab in Sheets.

```sql
CREATE TABLE IF NOT EXISTS daily_sku_pnl (
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
```

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL | Date |
| `sku` | TEXT | NOT NULL | Product SKU |
| `offer_id` | TEXT | NULLABLE | Offer ID |
| `product_name` | TEXT | NULLABLE | Product name |
| `quantity` | INTEGER | DEFAULT 0 | Quantity sold |
| `revenue` | NUMERIC(12,2) | DEFAULT 0 | Revenue |
| `cogs` | NUMERIC(12,2) | DEFAULT 0 | COGS for this SKU |
| `ad_spend` | NUMERIC(12,2) | DEFAULT 0 | Ad spend for this SKU |
| `gross_profit` | NUMERIC(12,2) | DEFAULT 0 | Gross profit for this SKU |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:**
```sql
CREATE INDEX idx_daily_sku_date ON daily_sku_pnl(date);
```

**Unique constraints:** `UNIQUE(date, sku)` — one row per SKU per day.

**Foreign keys:** None — aggregated data.

**Volume estimate:**
- Per day: 20-200 rows (active SKUs)
- Per month: 600-6,000 rows
- Growth: linear with SKU count
- Retention: 90 days recommended

---

### 2.8 `daily_control` — Plan vs Actual Control

**Purpose:** Store daily control metrics for operational monitoring. Includes plan comparison and run-rate.

```sql
CREATE TABLE IF NOT EXISTS daily_control (
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

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `date` | DATE | NOT NULL, UNIQUE | One row per day |
| `orders` | INTEGER | DEFAULT 0 | Order count |
| `revenue` | NUMERIC(12,2) | DEFAULT 0 | Revenue |
| `commission` | NUMERIC(12,2) | DEFAULT 0 | Commission |
| `advertising` | NUMERIC(12,2) | DEFAULT 0 | Ad spend |
| `cogs` | NUMERIC(12,2) | DEFAULT 0 | COGS |
| `logistics` | NUMERIC(12,2) | DEFAULT 0 | Logistics |
| `gross_profit` | NUMERIC(12,2) | DEFAULT 0 | Gross profit |
| `margin_pct` | NUMERIC(6,2) | DEFAULT 0 | Margin % |
| `plan_vp` | NUMERIC(12,2) | DEFAULT 0 | Planned gross profit |
| `deviation` | NUMERIC(12,2) | DEFAULT 0 | Actual - Plan |
| `cumulative_vp` | NUMERIC(12,2) | DEFAULT 0 | Cumulative VP for month |
| `run_rate` | NUMERIC(12,2) | DEFAULT 0 | Projected monthly VP |
| `status` | TEXT | DEFAULT 'NO DATA' | OK / BELOW PLAN / NO DATA |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |

**Indexes:** None needed — UNIQUE on date, small table.

**Unique constraints:** `date` UNIQUE — one control row per day.

**Foreign keys:** None — aggregated data.

**Volume estimate:**
- Static: 1 row per day
- Per year: 365 rows
- Growth: +1 row/day
- Retention: indefinite

---

### 2.9 `alerts` — Alert History

**Purpose:** Store alert events for monitoring and audit. Deduplication via signature.

```sql
CREATE TABLE IF NOT EXISTS alerts (
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

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID PK | NOT NULL | Primary key |
| `alert_type` | TEXT | NOT NULL | low_margin, high_drr, no_sales, low_stock, high_commission, spend_no_orders |
| `severity` | TEXT | NOT NULL | high, medium, low |
| `message` | TEXT | NOT NULL | Human-readable alert message |
| `metric_value` | NUMERIC(12,2) | NULLABLE | Actual metric value |
| `threshold` | NUMERIC(12,2) | NULLABLE | Threshold that was breached |
| `sku` | TEXT | NULLABLE | SKU if alert is per-product |
| `signature` | TEXT | NOT NULL | SHA-1 for deduplication |
| `acknowledged` | BOOLEAN | DEFAULT FALSE | User acknowledgment |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Alert creation time |

**Indexes:**
```sql
CREATE INDEX idx_alerts_date ON alerts(created_at DESC);
CREATE INDEX idx_alerts_signature ON alerts(signature);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
```

**Unique constraints:** None — signature used for deduplication at application level.

**Foreign keys:** None — independent logging.

**Volume estimate:**
- Per day: 0-10 alerts
- Per month: 0-300 rows
- Growth: minimal
- Retention: 90 days recommended

---

## 3. Summary: All New Tables

| Table | Rows/Day | Rows/Month | Retention | Priority |
|-------|----------|------------|-----------|----------|
| `finance_transactions` | 50-500 | 1,500-15,000 | 90 days | HIGH |
| `postings` | 20-200 | 600-6,000 | 90 days | HIGH |
| `performance_campaigns` | 0-5 | 0-150 | indefinite | MEDIUM |
| `performance_stats` | 50-500 | 1,500-15,000 | 90 days | HIGH |
| `cogs` | 0-5 | 0-150 | indefinite | HIGH |
| `daily_pnl` | 1 | 30 | indefinite | HIGH |
| `daily_sku_pnl` | 20-200 | 600-6,000 | 90 days | MEDIUM |
| `daily_control` | 1 | 30 | indefinite | HIGH |
| `alerts` | 0-10 | 0-300 | 90 days | MEDIUM |

**Total new tables: 9**

---

## 4. Views to Update

### Update `v_daily_pnl`

Current view uses `p.cost_price` for COGS. Should be updated to use `cogs` table when available, falling back to `products.cost_price`.

```sql
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT
    p.id AS product_id,
    p.offer_id,
    p.sku,
    p.name,
    s.date,
    COALESCE(s.revenue, 0) AS revenue,
    COALESCE(s.quantity, 0) AS quantity,
    COALESCE(s.returns_amount, 0) AS returns,
    COALESCE(f.advertising, 0) AS advertising,
    COALESCE(f.ozon_commission, 0) AS commission,
    COALESCE(f.logistics, 0) AS logistics,
    COALESCE(f.partner_services, 0) AS partner_services,
    COALESCE(f.fbo_services, 0) AS fbo_services,
    COALESCE(fi.sales, 0) AS finance_sales,
    COALESCE(fi.returns, 0) AS finance_returns,
    COALESCE(fi.commission, 0) AS finance_commission,
    COALESCE(fi.advertising, 0) AS finance_advertising,
    COALESCE(c.unit_cost, p.cost_price, 0) * COALESCE(s.quantity, 0) AS cogs,
    COALESCE(s.revenue, 0)
        - COALESCE(f.ozon_commission, 0)
        - COALESCE(f.logistics, 0)
        - COALESCE(f.partner_services, 0)
        - COALESCE(f.fbo_services, 0)
        - COALESCE(f.advertising, 0)
        - COALESCE(c.unit_cost, p.cost_price, 0) * COALESCE(s.quantity, 0) AS gross_profit
FROM products p
LEFT JOIN sales s ON s.product_id = p.id
LEFT JOIN finance f ON f.date = s.date
LEFT JOIN finance_items fi ON fi.finance_id = f.id AND fi.product_id = p.id
LEFT JOIN cogs c ON c.sku = p.sku;
```

---

## 5. Migration Order

```sql
-- Migration 004: Daily P&L Engine
-- Date: 2026-06-20

BEGIN;

-- 1. Raw data tables
CREATE TABLE IF NOT EXISTS finance_transactions (...);
CREATE TABLE IF NOT EXISTS postings (...);
CREATE TABLE IF NOT EXISTS performance_campaigns (...);
CREATE TABLE IF NOT EXISTS performance_stats (...);

-- 2. COGS management
CREATE TABLE IF NOT EXISTS cogs (...);

-- 3. Aggregated daily tables
CREATE TABLE IF NOT EXISTS daily_pnl (...);
CREATE TABLE IF NOT EXISTS daily_sku_pnl (...);
CREATE TABLE IF NOT EXISTS daily_control (...);

-- 4. Alerts
CREATE TABLE IF NOT EXISTS alerts (...);

-- 5. Indexes
CREATE INDEX ...;

-- 6. Update existing view
CREATE OR REPLACE VIEW v_daily_pnl AS ...;

COMMIT;
```

---

## 6. Rollback Strategy

Each table uses `CREATE TABLE IF NOT EXISTS` — safe to re-run.

**Full rollback:**
```sql
BEGIN;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS daily_control CASCADE;
DROP TABLE IF EXISTS daily_sku_pnl CASCADE;
DROP TABLE IF EXISTS daily_pnl CASCADE;
DROP TABLE IF EXISTS cogs CASCADE;
DROP TABLE IF EXISTS performance_stats CASCADE;
DROP TABLE IF EXISTS performance_campaigns CASCADE;
DROP TABLE IF EXISTS postings CASCADE;
DROP TABLE IF EXISTS finance_transactions CASCADE;
-- Restore old view
CREATE OR REPLACE VIEW v_daily_pnl AS ...;
COMMIT;
```

**Risk:** Dropping tables loses data. Backup before rollback.

---

## 7. Migration Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Large volume in finance_transactions | LOW | Use INSERT ON CONFLICT, batch inserts |
| Duplicate data from re-fetches | LOW | No UNIQUE on raw tables, application dedup |
| View update breaks existing queries | MEDIUM | Test view with existing data before applying |
| COGS table conflicts with products.cost_price | LOW | COGS table is authoritative, products.cost_price is fallback |
| Performance on daily_pnl queries | LOW | UNIQUE on date, small table |
| UUID generation overhead | LOW | Use gen_random_uuid() (pg 13+ fast) |
| Migration runs on production | HIGH | Test on staging first, have rollback ready |

---

## 8. Verification Checklist

After migration:
- [ ] All 9 tables created
- [ ] All indexes created
- [ ] Unique constraints working
- [ ] v_daily_pnl view updated and returns correct data
- [ ] INSERT/SELECT works on all tables
- [ ] Rollback script works
- [ ] No conflicts with existing migrations
