---
taskId: task_015
epicId: EP-AE-004
parentStories: [us_013]
title: "Audit Log Persistence & Reproducibility Validation"
priority: P1-High
status: PLANNED
estimatedHours: 6
---

# Task: Audit Log Persistence & Reproducibility Validation

## Objective

Implement append-only audit log persistence and reproducibility validation. Enable re-verification of findings from logged artifacts without pipeline re-run. Support 95%+ reproducibility target.

---

## Acceptance Criteria Mapping

- **us_013 AC-1:** Audit log persisted, append-only (no UPDATE/DELETE)
- **us_013 AC-2:** ≥95% findings reproducible from logged artifacts
- **us_013 AC-3:** Reproducibility validation performed and logged
- **us_013 AC-4:** Audit outcome recorded (VALIDATED, UNVALIDATED, ERROR)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/reproducibility.py` | CREATE | Reproducibility validator, artifact archival |
| `shared/database/migrations/004_audit_log_reproducibility.sql` | CREATE | Audit log schema extensions |
| `shared/database/models.py` | MODIFY | SQLAlchemy ORM for audit log |

---

## Reproducibility Validation Strategy

**Process:**
1. After batch execution, archive input resources snapshot (SHA256 hash + optional JSON)
2. For each finding, store:
   - finding_id, rule_id, rule_version
   - input_snapshot_hash (SHA256)
   - output_finding_hash (SHA256)
   - audit_outcome (VALIDATED, UNVALIDATED, ERROR)
   - timestamp_utc
3. On reproducibility audit: re-run same batch with same rule version, compare findings

**Validation Method:**
- Re-execute batch with archived rule pack version
- For each archived finding, verify:
  - Same input_snapshot_hash exists → Same output_finding_hash?
  - If yes → VALIDATED
  - If no → UNVALIDATED (unexpected divergence)
  - If error → ERROR (rule execution failed)
- Report: total_findings, validated_count, unvalidated_count, error_count
- Pass if validated_count / total_findings ≥ 95%

---

## Implementation Checklist

- [ ] Create ReproducibilityValidator class
- [ ] Implement input_snapshot_hash computation (SHA256 of input resources)
- [ ] Implement output_finding_hash computation (SHA256 of Finding object)
- [ ] Implement artifact archival (store input snapshot, hashes, metadata)
- [ ] Create audit_log table (append-only, no UPDATE/DELETE)
- [ ] Implement audit log writer (batch_run_id, findings_count, status, timestamp)
- [ ] Implement reproducibility verification routine (re-execute batch, compare hashes)
- [ ] Generate reproducibility report (validated %, unvalidated %, error %)
- [ ] Add configuration for hash algorithm (SHA256) and verification frequency
- [ ] Write unit tests (≥4 scenarios: hash computation, artifact storage, verification)

---

## Database Schema Extensions

### audit_log Table (APPEND-ONLY)
```
id (SERIAL PK)
batch_run_id (UUID, UNIQUE, FK → execution_plans.batch_run_id)
rule_pack_version (VARCHAR)
cohort_size (INT)
findings_count (INT)
validated_findings_count (INT, nullable — set after reproducibility audit)
unvalidated_findings_count (INT, nullable)
error_count (INT, nullable)
status (VARCHAR: SUCCESS, PARTIAL_SUCCESS, FAILED)
reproducibility_status (VARCHAR: VERIFIED, UNVERIFIED, INVALID)
created_at (TIMESTAMP DEFAULT NOW())
verified_at (TIMESTAMP, nullable — set when reproducibility audit completes)
```

### finding_hashes Table
```
id (SERIAL PK)
finding_id (UUID, FK → findings.finding_id, not null, UNIQUE)
input_snapshot_hash (VARCHAR(64) — SHA256 hex)
output_finding_hash (VARCHAR(64) — SHA256 hex)
reproducible (BOOLEAN DEFAULT FALSE — set after verification)
audit_outcome (VARCHAR: VALIDATED, UNVALIDATED, ERROR)
created_at (TIMESTAMP DEFAULT NOW())
verified_at (TIMESTAMP, nullable)
```

---

## Technical Notes

- Append-only constraint: Enforce in application code (no DELETE operations)
- Hash algorithm: SHA256 (Python hashlib.sha256)
- Hashing inputs: JSON-serialized objects with deterministic key ordering
- Artifact storage: Optional (can store full JSON or just hashes)
- Verification frequency: Post-batch by default; on-demand reproducibility audits
- Report format: Markdown with tables (findings_count, percentages, timing)

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| INPUT_snapshot_hash collision | Log ERROR; continue (highly unlikely with SHA256) |
| output_finding_hash mismatch | Log UNVALIDATED; investigate rule version or data changes |
| Audit log INSERT fails | Log CRITICAL; raise exception (batch cannot complete) |
| Input snapshot JSON too large | Truncate to 10MB; log WARN; store only hash |
| Reproducibility audit long-running | Implement timeout (default 1 hour per batch); allow async verification |

---

## Definition of Done

- [ ] Reproducibility validator implemented
- [ ] Input/output hashing working (deterministic, SHA256)
- [ ] Artifact archival functional
- [ ] Audit log schema created (append-only)
- [ ] Audit log writer working
- [ ] Reproducibility verification routine working
- [ ] Verification pass threshold ≥95%
- [ ] Reproducibility report generated (markdown)
- [ ] Unit tests pass (≥4 scenarios)
- [ ] No linting issues
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_008 (Finding model with hashes), task_014 (Severity/hydration before audit)
- **Blocked By:** None
- **Related:** task_016 (Testing)

---

**Effort:** 6 hours  
**Owner:** Backend + Database Engineer (split: 3 hours backend logic, 3 hours DB schema)  
**Review Checklist:** Hashing deterministic, archival working, audit log append-only, verification ≥95%, tests pass
