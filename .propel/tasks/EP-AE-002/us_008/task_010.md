---
taskId: task_010
epicId: EP-AE-002
parentStories: [us_005, us_006, us_007, us_008]
title: "Database Schema: Findings & Evidence"
priority: P1-High
status: PLANNED
estimatedHours: 6
---

# Task: Database Schema - Findings & Evidence

## Objective

Design and implement PostgreSQL schema for findings storage, evidence persistence, and query optimization. Support reproducibility lookups and audit trail integration.

---

## Acceptance Criteria Mapping

- **us_008 AC-5:** Findings persisted to database with reproducibility tracking
- **us_005-008 AC (aggregate):** Evidence queryable, indexed for fast retrieval

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `shared/database/migrations/002_findings_and_evidence.sql` | CREATE | Schema for findings, evidence, findings_hashes |
| `shared/database/models.py` | MODIFY | SQLAlchemy ORM models for Finding, Evidence |

---

## Schema Design

### findings Table
```
id (SERIAL PK)
finding_id (UUID, UNIQUE, not null)
rule_id (VARCHAR)
rule_version (VARCHAR)
batch_run_id (UUID FK → execution_plans.batch_run_id)
timestamp_utc (TIMESTAMP, DEFAULT NOW())
audit_outcome (VARCHAR: CONTRADICTED, FLAGGED, etc.)
severity_tier (VARCHAR: CRITICAL, HIGH, MEDIUM, LOW)
patient_id (VARCHAR)
resources_evaluated (TEXT[] — array of resource references)
resource_count (INT)
evidence_completeness_pct (FLOAT)
rule_logic_summary (TEXT)
finding_narrative (TEXT)
status (VARCHAR: EMITTED, VALIDATED, SUPERSEDED)
created_at (TIMESTAMP DEFAULT NOW())
reproducible (BOOLEAN DEFAULT FALSE)
reproducibility_notes (TEXT, nullable)
```

### finding_evidence Table
```
id (SERIAL PK)
finding_id (UUID FK → findings.finding_id, not null, on_delete=cascade)
evidence_key (VARCHAR — e.g., "contradiction_type")
evidence_value (JSONB — structured evidence sub-object)
created_at (TIMESTAMP DEFAULT NOW())
```

### finding_hashes Table
```
id (SERIAL PK)
finding_id (UUID FK → findings.finding_id, not null, UNIQUE)
input_snapshot_hash (VARCHAR(64) — SHA256 hex)
output_finding_hash (VARCHAR(64) — SHA256 hex)
input_snapshot_json (JSONB, optional — full input snapshot)
created_at (TIMESTAMP DEFAULT NOW())
```

---

## Implementation Checklist

- [ ] Create findings table (all fields, indexes on finding_id, batch_run_id, patient_id, rule_id)
- [ ] Create finding_evidence table (JSONB for evidence flexibility)
- [ ] Create finding_hashes table (SHA256 hashes for reproducibility)
- [ ] Add foreign key constraints (FK to execution_plans.batch_run_id)
- [ ] Define indexes: batch_run_id, patient_id, rule_id, timestamp_utc, severity_tier
- [ ] Add JSONB index on evidence_value (for full-text search capabilities)
- [ ] Create SQLAlchemy ORM models (Finding, FindingEvidence, FindingHash)
- [ ] Write schema documentation (ERD, field descriptions)

---

## Technical Notes

- Findings table: normalized design with finding_id as primary key
- Evidence table: separate for flexibility (JSONB allows unstructured evidence)
- Hashes table: dedicated to reproducibility verification (task_015)
- Indexes on common queries: batch_run_id (findings per batch), patient_id (findings per patient)
- JSONB: PostgreSQL native JSON type, queryable via -> operators
- Array type (resources_evaluated): TEXT[] for fast lookups
- Timestamps: all UTC, DEFAULT NOW() at table level

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Duplicate finding_id | UNIQUE constraint prevents; app must guarantee unique IDs |
| FK violation (batch_run_id not found) | Constraint enforced; app must create batch before findings |
| Evidence table becomes very large | Create index on evidence_key; consider partitioning by month |
| Hash collision (unlikely but) | Log ERROR; app-level verification in task_015 |
| Very large evidence_value JSON | PostgreSQL handles; query performance monitored |

---

## Definition of Done

- [ ] All 3 tables created (findings, finding_evidence, finding_hashes)
- [ ] Indexes created on key columns (batch_run_id, patient_id, rule_id, etc.)
- [ ] Foreign key constraints defined and tested
- [ ] SQLAlchemy ORM models created and working
- [ ] Migration file syntax correct (psql executable)
- [ ] Schema documented (ERD, field descriptions)
- [ ] No unused columns
- [ ] Code review approved

---

## Dependencies

- **Blocking:** None
- **Blocked By:** None
- **Related:** task_007-008 (Findings generated), task_015 (Reproducibility validation)

---

## Validation Strategy

- Manual: Run migration on test PostgreSQL, verify tables created
- Manual: Insert sample findings, verify indexes working
- Schema review: Check for missing columns, naming consistency

---

**Effort:** 6 hours  
**Sequencing:** Parallel with task_007-008 (backend)  
**Owner:** Database Engineer  
**Review Checklist:** Schema complete, indexes created, ORM models working, migration executable
