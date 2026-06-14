-- Ozon AI Agent - Data Warehouse Schema
-- Version: 001
-- Date: 2026-06-13

BEGIN;

-- ============================================
-- PRODUCTS
-- ============================================
CREATE TABLE IF NOT EXISTS products (
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

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_offer_id ON products(offer_id);

-- Product price history
CREATE TABLE IF NOT EXISTS product_prices (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    price NUMERIC(12,2),
    old_price NUMERIC(12,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_product_prices_product_date ON product_prices(product_id, recorded_at);

-- ============================================
-- STOCKS
-- ============================================
CREATE TABLE IF NOT EXISTS stocks (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    warehouse VARCHAR(255),
    stock_total INT DEFAULT 0,
    stock_fbo INT DEFAULT 0,
    stock_fbs INT DEFAULT 0,
    in_transit INT DEFAULT 0,
    reserved INT DEFAULT 0,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stocks_product_date ON stocks(product_id, recorded_at);

-- ============================================
-- ORDERS
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
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
    scheme VARCHAR(10), -- FBO, FBS
    region VARCHAR(255),
    city VARCHAR(255),
    created_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_product_date ON orders(product_id, created_at);
CREATE INDEX idx_orders_status ON orders(status);

-- ============================================
-- SALES (aggregated from orders)
-- ============================================
CREATE TABLE IF NOT EXISTS sales (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    date DATE NOT NULL,
    quantity INT DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    returns INT DEFAULT 0,
    returns_amount NUMERIC(12,2) DEFAULT 0,
    avg_price NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, date)
);

CREATE INDEX idx_sales_product_date ON sales(product_id, date);

-- ============================================
-- ADVERTISING (Performance API)
-- ============================================
CREATE TABLE IF NOT EXISTS advertising (
    id BIGSERIAL PRIMARY KEY,
    campaign_id VARCHAR(255) NOT NULL,
    product_id BIGINT REFERENCES products(id),
    offer_id VARCHAR(255),
    sku VARCHAR(255),
    date DATE NOT NULL,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    ctr NUMERIC(8,4),
    spend NUMERIC(12,2) DEFAULT 0,
    orders INT DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    avg_cpc NUMERIC(12,2),
    avg_cpm NUMERIC(12,2),
    drr NUMERIC(8,4),
    campaign_name VARCHAR(500),
    campaign_status VARCHAR(50),
    payment_type VARCHAR(100),
    placement VARCHAR(255),
    budget NUMERIC(12,2),
    daily_budget NUMERIC(12,2),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id, product_id, date)
);

CREATE INDEX idx_advertising_product_date ON advertising(product_id, date);
CREATE INDEX idx_advertising_campaign_date ON advertising(campaign_id, date);

-- ============================================
-- SEARCH POSITIONS
-- ============================================
CREATE TABLE IF NOT EXISTS search_positions (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    query TEXT NOT NULL,
    position INT,
    page INT,
    is_sponsored BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_product_query ON search_positions(product_id, query, recorded_at);

-- ============================================
-- COMPETITORS
-- ============================================
CREATE TABLE IF NOT EXISTS competitors (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    competitor_offer_id VARCHAR(255),
    competitor_name TEXT,
    competitor_price NUMERIC(12,2),
    competitor_rating NUMERIC(3,2),
    competitor_reviews INT,
    competitor_stock_status VARCHAR(50),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitors_product ON competitors(product_id, recorded_at);

-- ============================================
-- REVIEWS
-- ============================================
CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    review_id VARCHAR(255),
    rating INT,
    text TEXT,
    pros TEXT,
    cons TEXT,
    author VARCHAR(255),
    is_positive BOOLEAN,
    photos_count INT DEFAULT 0,
    created_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reviews_product ON reviews(product_id, created_at);

-- Review aggregation by date
CREATE TABLE IF NOT EXISTS review_stats (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    date DATE NOT NULL,
    total_reviews INT DEFAULT 0,
    avg_rating NUMERIC(3,2),
    positive_count INT DEFAULT 0,
    negative_count INT DEFAULT 0,
    rating_1 INT DEFAULT 0,
    rating_2 INT DEFAULT 0,
    rating_3 INT DEFAULT 0,
    rating_4 INT DEFAULT 0,
    rating_5 INT DEFAULT 0,
    UNIQUE(product_id, date)
);

CREATE INDEX idx_review_stats_product_date ON review_stats(product_id, date);

-- ============================================
-- FINANCE
-- ============================================
CREATE TABLE IF NOT EXISTS finance (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    sales NUMERIC(12,2) DEFAULT 0,
    returns NUMERIC(12,2) DEFAULT 0,
    ozon_commission NUMERIC(12,2) DEFAULT 0,
    logistics NUMERIC(12,2) DEFAULT 0,
    partner_services NUMERIC(12,2) DEFAULT 0,
    fbo_services NUMERIC(12,2) DEFAULT 0,
    other_services NUMERIC(12,2) DEFAULT 0,
    advertising NUMERIC(12,2) DEFAULT 0,
    accrued_total NUMERIC(12,2) DEFAULT 0,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date)
);

CREATE INDEX idx_finance_date ON finance(date);

-- Finance by product
CREATE TABLE IF NOT EXISTS finance_items (
    id BIGSERIAL PRIMARY KEY,
    finance_id BIGINT REFERENCES finance(id),
    product_id BIGINT REFERENCES products(id),
    sales NUMERIC(12,2) DEFAULT 0,
    returns NUMERIC(12,2) DEFAULT 0,
    commission NUMERIC(12,2) DEFAULT 0,
    logistics NUMERIC(12,2) DEFAULT 0,
    advertising NUMERIC(12,2) DEFAULT 0
);

CREATE INDEX idx_finance_items_finance ON finance_items(finance_id);

-- ============================================
-- LOGISTICS
-- ============================================
CREATE TABLE IF NOT EXISTS logistics (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    warehouse VARCHAR(255),
    delivery_days_avg NUMERIC(5,2),
    delivery_cost NUMERIC(12,2),
    return_rate NUMERIC(5,4),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logistics_product ON logistics(product_id, recorded_at);

-- ============================================
-- EXPERIMENTS
-- ============================================
CREATE TABLE IF NOT EXISTS experiments (
    id BIGSERIAL PRIMARY KEY,
    experiment_id VARCHAR(100) UNIQUE NOT NULL,
    hypothesis TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'planned',
    target_metric VARCHAR(100),
    expected_result TEXT,
    actual_result TEXT,
    confidence_level NUMERIC(5,4),
    is_successful BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_changes (
    id BIGSERIAL PRIMARY KEY,
    experiment_id VARCHAR(100) REFERENCES experiments(experiment_id),
    product_id BIGINT REFERENCES products(id),
    change_type VARCHAR(50), -- price, bid, budget, stock
    old_value NUMERIC(12,2),
    new_value NUMERIC(12,2),
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- DECISIONS (Decision Engine log)
-- ============================================
CREATE TABLE IF NOT EXISTS decisions (
    id BIGSERIAL PRIMARY KEY,
    decision_id VARCHAR(100) UNIQUE NOT NULL,
    product_id BIGINT REFERENCES products(id),
    decision_type VARCHAR(50), -- increase_bid, decrease_price, restock, pause_campaign
    parameters JSONB,
    predicted_effect TEXT,
    predicted_impact NUMERIC(12,2),
    confidence NUMERIC(5,4),
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, applied, rejected
    experiment_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ
);

CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_product ON decisions(product_id);

-- ============================================
-- ETL LOG
-- ============================================
CREATE TABLE IF NOT EXISTS etl_log (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- running, success, failed
    rows_fetched INT DEFAULT 0,
    rows_inserted INT DEFAULT 0,
    rows_updated INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_etl_log_source ON etl_log(source, started_at);

-- ============================================
-- VIEWS
-- ============================================

-- Daily P&L per product
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
    COALESCE(p.cost_price, 0) * COALESCE(s.quantity, 0) AS cogs,
    COALESCE(s.revenue, 0)
        - COALESCE(f.ozon_commission, 0)
        - COALESCE(f.logistics, 0)
        - COALESCE(f.partner_services, 0)
        - COALESCE(f.fbo_services, 0)
        - COALESCE(f.advertising, 0)
        - COALESCE(p.cost_price, 0) * COALESCE(s.quantity, 0) AS gross_profit
FROM products p
LEFT JOIN sales s ON s.product_id = p.id
LEFT JOIN finance f ON f.date = s.date
LEFT JOIN finance_items fi ON fi.finance_id = f.id AND fi.product_id = p.id;

-- SKU performance summary
CREATE OR REPLACE VIEW v_sku_performance AS
SELECT
    p.id AS product_id,
    p.offer_id,
    p.sku,
    p.name,
    SUM(s.quantity) AS total_quantity,
    SUM(s.revenue) AS total_revenue,
    SUM(a.spend) AS total_spend,
    CASE WHEN SUM(s.revenue) > 0
        THEN ROUND(SUM(a.spend) / SUM(s.revenue) * 100, 2)
        ELSE 0
    END AS drr,
    AVG(rs.avg_rating) AS avg_rating,
    SUM(rs.total_reviews) AS total_reviews
FROM products p
LEFT JOIN sales s ON s.product_id = p.id
LEFT JOIN advertising a ON a.product_id = p.id
LEFT JOIN review_stats rs ON rs.product_id = p.id
GROUP BY p.id, p.offer_id, p.sku, p.name;

COMMIT;
