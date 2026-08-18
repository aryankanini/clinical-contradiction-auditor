-- Record reproducibility verification without modifying append-only audit facts.

CREATE TABLE IF NOT EXISTS audit_log_reproducibility (
    id SERIAL PRIMARY KEY,
    batch_run_id UUID NOT NULL REFERENCES execution_plans(batch_run_id) ON DELETE RESTRICT,
    validated_findings_count INTEGER NOT NULL DEFAULT 0,
    unvalidated_findings_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    reproducibility_status VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_audit_log_reproducibility_status CHECK (reproducibility_status IN ('VERIFIED', 'UNVERIFIED', 'INVALID'))
);

CREATE INDEX IF NOT EXISTS ix_audit_log_reproducibility_batch ON audit_log_reproducibility(batch_run_id);