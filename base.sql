
-- =====================================================
-- CINEMATCH DATABASE SCHEMAS
-- =====================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;


-- =====================================================
-- OPS 1: INGESTION RUNS
-- Tracks every TMDB ingestion pipeline execution
-- =====================================================

CREATE TABLE IF NOT EXISTS ops.ingestion_runs (

    run_id UUID PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'running',

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,

    records_processed BIGINT NOT NULL DEFAULT 0,
    records_succeeded BIGINT NOT NULL DEFAULT 0,
    records_failed BIGINT NOT NULL DEFAULT 0,

    error_message TEXT,

    CONSTRAINT chk_ingestion_runs_status
        CHECK (status IN ('running', 'success', 'failed')),

    CONSTRAINT chk_ingestion_runs_counts
        CHECK (
            records_processed >= 0
            AND records_succeeded >= 0
            AND records_failed >= 0
        ),

    CONSTRAINT chk_ingestion_runs_processed
        CHECK (
            records_succeeded + records_failed <= records_processed
        ),

    CONSTRAINT chk_ingestion_runs_finished_at
        CHECK (
            (status = 'running' AND finished_at IS NULL)
            OR
            (status IN ('success', 'failed') AND finished_at IS NOT NULL)
        ),

    CONSTRAINT chk_ingestion_runs_timestamps
        CHECK (
            finished_at IS NULL OR finished_at >= started_at
        )
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at
    ON ops.ingestion_runs (started_at DESC);


-- =====================================================
-- OPS 2: INGESTION CHECKPOINTS
-- Tracks ingestion progress and recovery
-- =====================================================

CREATE TABLE IF NOT EXISTS ops.ingestion_checkpoints (

    checkpoint_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source VARCHAR(50) NOT NULL DEFAULT 'tmdb',

    media_type VARCHAR(10) NOT NULL,

    export_date DATE NOT NULL,

    -- Last successfully completed TMDB ID
    last_processed_id BIGINT,

    -- Total successfully processed records
    records_processed BIGINT NOT NULL DEFAULT 0,

    last_processed_at TIMESTAMPTZ,

    last_run_id UUID
        REFERENCES ops.ingestion_runs(run_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_ingestion_checkpoints_media_type
        CHECK (media_type IN ('movie', 'tv')),

    CONSTRAINT chk_ingestion_checkpoints_records
        CHECK (records_processed >= 0),

    CONSTRAINT chk_ingestion_checkpoints_last_id
        CHECK (
            last_processed_id IS NULL OR last_processed_id > 0
        ),

    CONSTRAINT uq_ingestion_checkpoints_source_media_date
        UNIQUE (source, media_type, export_date)
);


-- =====================================================
-- OPS 3: INGESTION ERRORS
-- Tracks errors during metadata ingestion
-- =====================================================

CREATE TABLE IF NOT EXISTS ops.ingestion_errors (

    error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id UUID
        REFERENCES ops.ingestion_runs(run_id),

    media_type VARCHAR(10) NOT NULL,
    tmdb_id BIGINT NOT NULL,

    error_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,

    http_status_code SMALLINT,

    retry_count INTEGER NOT NULL DEFAULT 0,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,

    CONSTRAINT chk_ingestion_errors_media_type
        CHECK (media_type IN ('movie', 'tv')),

    CONSTRAINT chk_ingestion_errors_tmdb_id
        CHECK (tmdb_id > 0),

    CONSTRAINT chk_ingestion_errors_retry_count
        CHECK (retry_count >= 0),

    CONSTRAINT chk_ingestion_errors_http_status
        CHECK (
            http_status_code IS NULL
            OR http_status_code BETWEEN 100 AND 599
        ),

    CONSTRAINT chk_ingestion_errors_resolution
        CHECK (
            (is_resolved = FALSE AND resolved_at IS NULL)
            OR
            (is_resolved = TRUE AND resolved_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_ingestion_errors_unresolved
    ON ops.ingestion_errors (occurred_at DESC)
    WHERE is_resolved = FALSE;

CREATE INDEX IF NOT EXISTS idx_ingestion_errors_entity
    ON ops.ingestion_errors (media_type, tmdb_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_errors_run_id
    ON ops.ingestion_errors (run_id);


-- =====================================================
-- OPS 4: API REQUEST LOGS
-- Tracks TMDB API request activity
-- =====================================================

CREATE TABLE IF NOT EXISTS ops.api_request_logs (

    request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id UUID
        REFERENCES ops.ingestion_runs(run_id),

    endpoint VARCHAR(255) NOT NULL,

    media_type VARCHAR(10),
    tmdb_id BIGINT,

    http_method VARCHAR(10) NOT NULL DEFAULT 'GET',
    http_status_code SMALLINT,

    response_time_ms INTEGER,

    is_success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,

    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_api_logs_media_type
        CHECK (
            media_type IS NULL
            OR media_type IN ('movie', 'tv')
        ),

    CONSTRAINT chk_api_logs_http_status
        CHECK (
            http_status_code IS NULL
            OR http_status_code BETWEEN 100 AND 599
        ),

    CONSTRAINT chk_api_logs_response_time
        CHECK (
            response_time_ms IS NULL
            OR response_time_ms >= 0
        ),

    CONSTRAINT chk_api_logs_tmdb_id
        CHECK (
            tmdb_id IS NULL OR tmdb_id > 0
        ),

    CONSTRAINT chk_api_logs_method
        CHECK (http_method = 'GET')
);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_run_id
    ON ops.api_request_logs (run_id);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_status
    ON ops.api_request_logs (http_status_code);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_requested_at
    ON ops.api_request_logs (requested_at DESC);


-- =====================================================
-- OPS 5: INGESTION METRICS
-- Stores ingestion performance metrics
-- =====================================================

CREATE TABLE IF NOT EXISTS ops.ingestion_metrics (

    metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES ops.ingestion_runs(run_id),

    media_type VARCHAR(10) NOT NULL,

    metric_name VARCHAR(100) NOT NULL,

    metric_value NUMERIC(20, 4) NOT NULL,

    metric_unit VARCHAR(30),

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_ingestion_metrics_media_type
        CHECK (media_type IN ('movie', 'tv', 'all')),

    CONSTRAINT chk_ingestion_metrics_value
        CHECK (metric_value >= 0)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_metrics_run_id
    ON ops.ingestion_metrics (run_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_metrics_name
    ON ops.ingestion_metrics (metric_name);

CREATE INDEX IF NOT EXISTS idx_ingestion_metrics_recorded_at
    ON ops.ingestion_metrics (recorded_at DESC);


-- =====================================================
-- END OF CINEMATCH BASE DATABASE STRUCTURE
-- =====================================================
