-- Rule execution persistence: pack versions -> plans -> ordered rules -> immutable audit facts.

CREATE TABLE IF NOT EXISTS rule_packs (
    id SERIAL PRIMARY KEY,
    rule_pack_id VARCHAR(128) NOT NULL,
    version VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL,
    CONSTRAINT uq_rule_packs_identity UNIQUE (rule_pack_id, version),
    CONSTRAINT ck_rule_packs_status CHECK (status IN ('ACTIVE', 'ARCHIVED', 'DEPRECATED'))
);

CREATE TABLE IF NOT EXISTS rule_pack_rules (
    id SERIAL PRIMARY KEY,
    rule_pack_id INTEGER NOT NULL REFERENCES rule_packs(id) ON DELETE CASCADE,
    rule_id VARCHAR(128) NOT NULL,
    rule_version VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    position_in_pack INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rule_pack_rules_identity UNIQUE (rule_pack_id, rule_id)
);

CREATE TABLE IF NOT EXISTS execution_plans (
    id SERIAL PRIMARY KEY,
    batch_run_id UUID NOT NULL UNIQUE,
    rule_pack_id INTEGER NOT NULL REFERENCES rule_packs(id) ON DELETE RESTRICT,
    status VARCHAR(32) NOT NULL DEFAULT 'PLANNED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    execution_time_ms INTEGER,
    CONSTRAINT ck_execution_plans_status CHECK (status IN ('PLANNED', 'EXECUTING', 'COMPLETE', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS execution_plan_rules (
    id SERIAL PRIMARY KEY,
    execution_plan_id INTEGER NOT NULL REFERENCES execution_plans(id) ON DELETE CASCADE,
    rule_id VARCHAR(128) NOT NULL,
    execution_order INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    execution_time_ms INTEGER,
    findings_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    CONSTRAINT uq_execution_plan_rules_order UNIQUE (execution_plan_id, execution_order),
    CONSTRAINT ck_execution_plan_rules_status CHECK (status IN ('PENDING', 'EXECUTING', 'COMPLETE', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    batch_run_id UUID NOT NULL UNIQUE,
    rule_pack_version VARCHAR(64) NOT NULL,
    rule_pack_id INTEGER NOT NULL REFERENCES rule_packs(id) ON DELETE RESTRICT,
    cohort_size INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    findings_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    execution_summary JSONB,
    CONSTRAINT ck_audit_trail_status CHECK (status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS ix_rule_pack_rules_rule_id ON rule_pack_rules(rule_id);
CREATE INDEX IF NOT EXISTS ix_execution_plans_rule_pack_id ON execution_plans(rule_pack_id);
CREATE INDEX IF NOT EXISTS ix_execution_plans_created_at ON execution_plans(created_at);
CREATE INDEX IF NOT EXISTS ix_execution_plan_rules_rule_id ON execution_plan_rules(rule_id);
CREATE INDEX IF NOT EXISTS ix_audit_trail_rule_pack_id ON audit_trail(rule_pack_id);
CREATE INDEX IF NOT EXISTS ix_audit_trail_created_at ON audit_trail(created_at);

CREATE OR REPLACE FUNCTION prevent_audit_trail_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_trail is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_trail_append_only ON audit_trail;
CREATE TRIGGER trg_audit_trail_append_only
BEFORE UPDATE OR DELETE ON audit_trail
FOR EACH ROW EXECUTE FUNCTION prevent_audit_trail_mutation();