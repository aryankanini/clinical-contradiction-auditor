-- Extend legacy finding persistence with reproducibility and evidence query fields.

ALTER TABLE findings ADD COLUMN IF NOT EXISTS finding_uuid UUID UNIQUE;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS rule_version VARCHAR(64);
ALTER TABLE findings ADD COLUMN IF NOT EXISTS batch_run_id UUID REFERENCES execution_plans(batch_run_id) ON DELETE RESTRICT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS patient_id VARCHAR(128);
ALTER TABLE findings ADD COLUMN IF NOT EXISTS resources_evaluated JSONB;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS resource_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS evidence_completeness_pct DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS rule_logic_summary TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS finding_narrative TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS reproducible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS reproducibility_notes TEXT;

ALTER TABLE finding_evidence ADD COLUMN IF NOT EXISTS evidence_key VARCHAR(128);

CREATE TABLE IF NOT EXISTS finding_hashes (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER NOT NULL UNIQUE REFERENCES findings(id) ON DELETE CASCADE,
    input_snapshot_hash VARCHAR(64) NOT NULL,
    output_finding_hash VARCHAR(64) NOT NULL,
    input_snapshot_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_findings_batch_run_id ON findings(batch_run_id);
CREATE INDEX IF NOT EXISTS ix_findings_patient_id ON findings(patient_id);
CREATE INDEX IF NOT EXISTS ix_findings_rule_id ON findings(rule_id);
CREATE INDEX IF NOT EXISTS ix_findings_created_at ON findings(created_at);
CREATE INDEX IF NOT EXISTS ix_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS ix_finding_evidence_key ON finding_evidence(evidence_key);
CREATE INDEX IF NOT EXISTS ix_finding_evidence_payload ON finding_evidence USING GIN(evidence_payload);