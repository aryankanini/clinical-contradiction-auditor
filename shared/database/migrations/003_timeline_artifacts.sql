-- Persist temporal rule context and lifecycle audit records.

CREATE TABLE IF NOT EXISTS timeline_findings (
    id SERIAL PRIMARY KEY,
    finding_id INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    timeline_type VARCHAR(32) NOT NULL,
    temporal_context JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stale_states (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(128),
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    last_updated TIMESTAMPTZ,
    age_years DOUBLE PRECISION NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finding_id INTEGER REFERENCES findings(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS state_transitions (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(128),
    resource_type VARCHAR(64) NOT NULL,
    previous_status VARCHAR(32),
    current_status VARCHAR(32) NOT NULL,
    transition_date TIMESTAMPTZ,
    valid BOOLEAN NOT NULL DEFAULT TRUE,
    finding_id INTEGER REFERENCES findings(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_timeline_findings_type ON timeline_findings(timeline_type);
CREATE INDEX IF NOT EXISTS ix_stale_states_patient_id ON stale_states(patient_id);
CREATE INDEX IF NOT EXISTS ix_stale_states_resource_type ON stale_states(resource_type);
CREATE INDEX IF NOT EXISTS ix_stale_states_detected_at ON stale_states(detected_at);
CREATE INDEX IF NOT EXISTS ix_state_transitions_patient_id ON state_transitions(patient_id);
CREATE INDEX IF NOT EXISTS ix_state_transitions_transition_date ON state_transitions(transition_date);