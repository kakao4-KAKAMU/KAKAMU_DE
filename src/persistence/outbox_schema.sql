CREATE TABLE IF NOT EXISTS ingest_outbox (
    id              BIGSERIAL PRIMARY KEY,
    aggregate_type  TEXT NOT NULL,
    op              TEXT NOT NULL DEFAULT 'upsert',
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_version  TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    content_hash    TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    attempts        INT NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_outbox_pending
    ON ingest_outbox (status, next_attempt_at)
    WHERE status IN ('pending', 'processing');

CREATE TABLE IF NOT EXISTS ingest_dlq (
    id              BIGSERIAL PRIMARY KEY,
    outbox_id       BIGINT,
    aggregate_type  TEXT NOT NULL,
    payload         JSONB NOT NULL,
    prompt_version  TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    last_error      TEXT,
    failed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
