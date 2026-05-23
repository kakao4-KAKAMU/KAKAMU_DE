CREATE TABLE IF NOT EXISTS eval_score (
    id              BIGSERIAL PRIMARY KEY,
    source_id       TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    judge_model     TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    scores          JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_score_source
    ON eval_score (source_type, source_id, created_at DESC);
