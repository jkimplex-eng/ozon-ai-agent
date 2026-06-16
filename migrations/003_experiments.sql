BEGIN;

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recommendation_id UUID,
    sku TEXT NOT NULL,
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    risk_level TEXT,
    confidence_score NUMERIC(8,4),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_by TEXT,
    notes TEXT
);

ALTER TABLE experiments
    DROP CONSTRAINT IF EXISTS experiments_status_check;

ALTER TABLE experiments
    ADD CONSTRAINT experiments_status_check
    CHECK (status IN ('DRAFT', 'READY', 'RUNNING', 'PAUSED', 'COMPLETED', 'CANCELLED', 'FAILED'));

CREATE INDEX IF NOT EXISTS idx_experiments_status_created
    ON experiments(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_experiments_sku_created
    ON experiments(sku, created_at DESC);

CREATE TABLE IF NOT EXISTS experiment_metrics (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC(16,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE experiment_metrics
    DROP CONSTRAINT IF EXISTS experiment_metrics_period_check;

ALTER TABLE experiment_metrics
    ADD CONSTRAINT experiment_metrics_period_check
    CHECK (period IN ('baseline', 'current', 'final'));

CREATE INDEX IF NOT EXISTS idx_experiment_metrics_experiment_period
    ON experiment_metrics(experiment_id, period, metric_name);

CREATE TABLE IF NOT EXISTS experiment_events (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_experiment_events_experiment_created
    ON experiment_events(experiment_id, created_at DESC);

CREATE TABLE IF NOT EXISTS experiment_outcomes (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success_score NUMERIC(8,4),
    direction_accuracy NUMERIC(8,4),
    actual_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_effect JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_experiment_outcomes_experiment
    ON experiment_outcomes(experiment_id);

COMMIT;
