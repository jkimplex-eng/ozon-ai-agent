BEGIN;

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sku TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    action TEXT NOT NULL,
    risk TEXT,
    confidence TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    recommendation_id TEXT,
    baseline_orders NUMERIC(12,2) DEFAULT 0,
    baseline_revenue NUMERIC(12,2) DEFAULT 0,
    baseline_drr NUMERIC(8,4) DEFAULT 0,
    current_orders NUMERIC(12,2) DEFAULT 0,
    current_revenue NUMERIC(12,2) DEFAULT 0,
    current_drr NUMERIC(8,4) DEFAULT 0,
    success_score NUMERIC(8,4),
    direction_accuracy NUMERIC(8,4),
    actual_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT,
    started_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    cancel_reason TEXT,
    fail_reason TEXT,
    created_by TEXT DEFAULT 'system'
);

ALTER TABLE experiments
    DROP CONSTRAINT IF EXISTS experiments_status_check;

ALTER TABLE experiments
    ADD CONSTRAINT experiments_status_check
    CHECK (status IN (
        'DRAFT', 'READY', 'RUNNING', 'PAUSED',
        'COMPLETED', 'CANCELLED', 'FAILED'
    ));

CREATE INDEX IF NOT EXISTS idx_experiments_status_created
    ON experiments(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_experiments_sku
    ON experiments(sku);

CREATE TABLE IF NOT EXISTS experiment_events (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor TEXT,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_experiment_events_experiment
    ON experiment_events(experiment_id, created_at DESC);

COMMIT;
