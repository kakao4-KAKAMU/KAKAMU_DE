CREATE TABLE IF NOT EXISTS bandit_arms (
    arm_id      TEXT PRIMARY KEY,
    context_key TEXT NOT NULL DEFAULT 'default',
    weights     JSONB NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS bandit_state (
    arm_id      TEXT NOT NULL,
    context_key TEXT NOT NULL DEFAULT 'default',
    alpha       DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    beta        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    n_pulls     INT NOT NULL DEFAULT 0,
    n_rewards   INT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (arm_id, context_key)
);
