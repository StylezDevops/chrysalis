-- Planted defect: not idempotent, so a second run (a retried deploy) fails.
CREATE TABLE release (
    id    BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL
);
