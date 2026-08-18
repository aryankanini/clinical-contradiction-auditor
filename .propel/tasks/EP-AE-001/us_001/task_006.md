---
taskId: task_006
epicId: EP-AE-001
parentStories: [us_001, us_002, us_003, us_004]
title: "Database Schema: Rule Packs & Execution Logs"
priority: P0-Critical
status: IN_PROGRESS
estimatedHours: 5
---

# Task: Database Schema - Rule Packs & Execution Logs

## Objective

Design and implement PostgreSQL schema for rule pack storage, execution plan logging, and audit trail persistence. Support versioning, immutability, and reproducibility requirements.

---

## Acceptance Criteria Mapping

- **us_002 AC-4:** Rule pack metadata persisted, versioned, retrievable
- **us_003 AC-2:** Execution plan logged before rule execution
- **us_004 AC-2:** Audit log append-only (no UPDATE/DELETE)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `shared/database/migrations/001_rule_packs_and_logs.sql` | CREATE | Schema for rule_packs, execution_plans, audit_trail tables |
| `shared/database/models.py` | MODIFY | SQLAlchemy ORM models for RulePack, ExecutionPlan, AuditLog |
| `shared/database/session.py` | MODIFY | Migration runner configuration |

---

## Implementation Checklist

- [x] Create `rule_packs` table (id PK, rule_pack_id, version, status, created_at, updated_at)
- [x] Create `rule_pack_rules` table (id, rule_pack_id FK, rule_id, rule_version, category)
- [x] Create `execution_plans` table (id PK, batch_run_id, rule_pack_id FK, status, created_at, executed_at)
- [x] Create `execution_plan_rules` table (id, execution_plan_id FK, rule_id, execution_order, status)
- [x] Create `audit_trail` table (id PK, batch_run_id, rule_pack_version, cohort_size, created_at, findings_count, status)
- [x] Add indexes on batch_run_id, rule_pack_id, rule_id for query performance
- [x] Add constraints: append-only (no DELETE on audit_trail), PK uniqueness
- [x] Define foreign key relationships and cascade rules
- [x] Create SQLAlchemy ORM models (RulePack, ExecutionPlan, AuditLog)
- [x] Write schema documentation (ERD comment, field descriptions)

---

## Schema Design

### rule_packs Table
```
id (SERIAL PK)
rule_pack_id (VARCHAR, UNIQUE)
version (VARCHAR, semver format, e.g., "1.0.0")
status (ENUM: ACTIVE, ARCHIVED, DEPRECATED)
created_at (TIMESTAMP DEFAULT NOW())
updated_at (TIMESTAMP DEFAULT NOW())
archived_at (TIMESTAMP, nullable)
```

### rule_pack_rules Table
```
id (SERIAL PK)
rule_pack_id (INT FK → rule_packs.id, not null, on_delete=cascade)
rule_id (VARCHAR)
rule_version (VARCHAR)
category (VARCHAR: diagnosis, medication, encounter, etc.)
position_in_pack (INT, for ordering)
created_at (TIMESTAMP DEFAULT NOW())
```

### execution_plans Table
```
id (SERIAL PK)
batch_run_id (UUID, UNIQUE)
rule_pack_id (INT FK → rule_packs.id, not null)
status (ENUM: PLANNED, EXECUTING, COMPLETE, FAILED)
created_at (TIMESTAMP DEFAULT NOW())
executed_at (TIMESTAMP, nullable)
completion_at (TIMESTAMP, nullable)
error_message (TEXT, nullable)
execution_time_ms (INT, nullable)
```

### execution_plan_rules Table
```
id (SERIAL PK)
execution_plan_id (INT FK → execution_plans.id, not null, on_delete=cascade)
rule_id (VARCHAR)
execution_order (INT, 1-based index in execution sequence)
status (ENUM: PENDING, EXECUTING, COMPLETE, FAILED)
execution_time_ms (INT, nullable)
findings_count (INT DEFAULT 0)
error_message (TEXT, nullable)
```

### audit_trail Table (APPEND-ONLY)
```
id (SERIAL PK)
batch_run_id (UUID FK → execution_plans.batch_run_id, not null, UNIQUE)
rule_pack_version (VARCHAR)
rule_pack_id (INT FK → rule_packs.id, not null)
cohort_size (INT)
created_at (TIMESTAMP DEFAULT NOW())
findings_count (INT DEFAULT 0)
status (ENUM: SUCCESS, PARTIAL_SUCCESS, FAILED)
execution_summary (JSON, optional structured summary)
```

---

## Technical Notes

- Append-only constraint: PostgreSQL doesn't enforce no-DELETE natively; enforce in ORM via read-only model
- Indexes on: batch_run_id, rule_pack_id, rule_id, created_at for typical queries
- Foreign keys: on_delete=cascade for execution_plan_rules, on_delete=restrict for audit_trail
- Versioning: rule_pack_version string stored for auditability (immutable after execution)
- JSON field (audit_trail.execution_summary) for extensibility without schema changes
- Status enums: modeled as PostgreSQL ENUM types or varchar + check constraints
- Timestamps: all UTC, DEFAULT NOW() at table level

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| rule_pack_id already exists | Constraint UNIQUE on rule_pack_id; INSERT fails with clear error |
| FK violation (rule_pack_id not found) | PostgreSQL constraint; app retries after creating rule pack |
| concurrent execution_plans for same batch | batch_run_id UNIQUE constraint prevents duplicates |
| audit_trail DELETE attempted | Implement read-only view in ORM; direct SQL DELETE blocked by app-level check |
| Migration fails mid-execution | Rollback to previous state; log error, halt startup |
| Very large audit_trail table | Recommend archival strategy (separate table partition), document in ops guide |

---

## Definition of Done

- [x] All 5 tables created (rule_packs, rule_pack_rules, execution_plans, execution_plan_rules, audit_trail)
- [x] Indexes created on key columns (batch_run_id, rule_pack_id, rule_id, created_at)
- [x] Foreign key constraints defined and tested
- [x] SQLAlchemy ORM models created (RulePack, ExecutionPlan, AuditLog)
- [x] Append-only constraint enforced (no DELETE on audit_trail in ORM)
- [ ] Migration file syntax correct (psql executable, no syntax errors)
- [x] Schema documented (field descriptions, ERD comment)
- [x] No unused columns; all fields justified
- [ ] Code review approved

---

## Dependencies

- **Blocking:** None (can be created parallel to backend tasks)
- **Blocked By:** None
- **Related:** task_001-004 (Backend tasks that use these tables)

---

## Validation Strategy

- Manual test: Run migration on test PostgreSQL instance, verify all tables created
- Manual test: Insert/query sample data, verify indexes working
- Manual test: Attempt DELETE on audit_trail, verify prevention
- Schema review: Check for missing columns, unused fields, naming consistency
- ORM test: Verify SQLAlchemy models map correctly to tables

---

## Testing Requirements

### Manual Tests
- `test_migration_creates_tables()` — Run migration 001; verify all 5 tables exist
- `test_foreign_key_constraints()` — Insert sample data; verify FK constraints work
- `test_append_only_constraint()` — Attempt DELETE on audit_trail; verify blocked
- `test_indexes_exist()` — Query pg_indexes; verify all expected indexes present
- `test_orm_models_map_correctly()` — Create ORM objects; verify column mapping

### Schema Review
- [ ] All required fields present (id, timestamps, status, foreign keys)
- [ ] No unused columns (every field has clear purpose)
- [ ] Naming consistency (snake_case, clear abbreviations)
- [ ] Primary and foreign keys properly defined
- [ ] Indexes on query-heavy columns

---

## External Resources

- PostgreSQL schema design: https://www.postgresql.org/docs/14/ddl.html
- SQLAlchemy ORM: https://docs.sqlalchemy.org/14/orm/
- Append-only tables: https://wiki.postgresql.org/wiki/Immutable_tables

---

**Effort:** 5 hours  
**Sequencing:** First database task (parallel with backend tasks, must complete before testing)  
**Owner:** Database Engineer  
**Review Checklist:** Schema complete, indexes created, ORM models working, append-only constraint verified, migration executable
