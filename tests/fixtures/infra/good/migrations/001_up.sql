-- Idempotent: running it twice leaves the same schema and raises no error (K12).
CREATE TABLE IF NOT EXISTS release (
    id         BIGSERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS release_created_at ON release (created_at);
