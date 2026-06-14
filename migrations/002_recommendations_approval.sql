BEGIN;

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sku TEXT NOT NULL,
    product_name TEXT,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence_score NUMERIC(8,4),
    confidence_level TEXT,
    risk_score NUMERIC(8,4),
    risk_level TEXT,
    expected_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    supporting_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    rejected_by TEXT,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    executed_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    source TEXT
);

ALTER TABLE recommendations
    DROP CONSTRAINT IF EXISTS recommendations_status_check;

ALTER TABLE recommendations
    ADD CONSTRAINT recommendations_status_check
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED', 'OBSERVED', 'CLOSED'));

CREATE INDEX IF NOT EXISTS idx_recommendations_status_created
    ON recommendations(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendations_sku_created
    ON recommendations(sku, created_at DESC);

CREATE TABLE IF NOT EXISTS recommendation_outcomes (
    id UUID PRIMARY KEY,
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observation_window_days INTEGER NOT NULL,
    expected_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    actual_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    forecast_error NUMERIC(8,4),
    success_score NUMERIC(8,4),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_recommendation
    ON recommendation_outcomes(recommendation_id, created_at DESC);

COMMIT;
