-- LLM judge daily evaluation scores (PostgreSQL)

CREATE TABLE IF NOT EXISTS eval_score (
    id              BIGSERIAL PRIMARY KEY,
    sample_id       TEXT NOT NULL,
    run_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    source_type     TEXT NOT NULL DEFAULT 'golden'
        CHECK (source_type IN ('golden', 'production')),
    input_text      TEXT NOT NULL,
    expected        JSONB,
    judge_output    JSONB NOT NULL,
    schema_score    REAL,
    themes_score    REAL,
    sentiment_score REAL,
    overall_score   REAL,
    cos_sim         REAL,
    failed          BOOLEAN NOT NULL DEFAULT FALSE,
    keywords        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_score_run_date
    ON eval_score (run_date DESC);

CREATE INDEX IF NOT EXISTS idx_eval_score_sample
    ON eval_score (sample_id, run_date DESC);
