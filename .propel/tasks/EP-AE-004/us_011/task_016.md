---
taskId: task_016
epicId: EP-AE-004
parentStories: [us_011, us_012, us_013]
title: "Severity, Transparency & Audit Log Tests; Documentation"
priority: P1-High
status: IN_PROGRESS
estimatedHours: 8
---

# Task: Severity, Transparency & Audit Log Tests; Documentation

## Objective

Develop comprehensive test suite for severity scoring, transparency hydration, and reproducibility validation. Create documentation for rule catalog, architecture, and deployment.

---

## Acceptance Criteria Mapping

- **us_011-013 (all AC):** Integration tests verify scoring, transparency, audit log, reproducibility

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `tests/unit/test_severity_and_audit.py` | CREATE | Unit tests for scoring, hydration, audit log |
| `tests/integration/test_audit_log_reproducibility.py` | CREATE | E2E reproducibility tests |
| `docs/rule-catalog.md` | CREATE | Rule definitions, weights, categories, examples |
| `docs/architecture-audit-engine.md` | CREATE | System design, data flows, reproducibility model |
| `docs/deployment-guide.md` | CREATE | Setup, configuration, operations |

---

## Implementation Checklist

**Testing:**
- [x] Unit test severity calculation (5+ scenarios: score computation, tier mapping)
- [x] Unit test transparency hydration (3+ scenarios: full hydration, partial, missing fields)
- [x] Unit test audit log write (append-only constraint)
- [x] Integration test: full pipeline with severity + transparency + audit
- [x] Integration test: reproducibility validation (verify ≥95% pass)
- [ ] Integration test: artifact archival and retrieval

**Documentation:**
- [x] Create rule catalog (all 18 rules with definitions, examples, severity weights)
- [x] Create architecture guide (system design, data flows, immutability model)
- [x] Create deployment guide (PostgreSQL setup, configuration, monitoring)
- [x] Create troubleshooting guide (common issues, debugging)

---

## Test Scenarios (15+ tests)

### Severity Tests (5 tests)
- test_severity_score_critical() — Score ≥10 → CRITICAL tier
- test_severity_score_high() — Score 7-9 → HIGH tier
- test_severity_score_medium() — Score 4-6 → MEDIUM tier
- test_severity_score_low() — Score <4 → LOW tier
- test_severity_determinism() — Same input → same score

### Transparency Tests (4 tests)
- test_hydration_all_fields() — All fields populated
- test_hydration_completeness() — ≥80% fields populated
- test_hydration_narrative_generated() — Finding narrative present
- test_hydration_hashes_computed() — Input/output hashes present

### Audit Log Tests (3 tests)
- test_audit_log_append_only() — INSERT only, no UPDATE/DELETE
- test_audit_log_batch_entry() — Batch entry created with correct metadata
- test_audit_log_finding_hashes() — Finding hashes stored and retrievable

### Reproducibility Tests (3+ tests)
- test_reproducibility_validation_pass() — ≥95% findings validated
- test_reproducibility_validation_fail() — <95% findings validated (error case)
- test_reproducibility_artifact_archival() — Input snapshots stored and retrievable
- test_reproducibility_hash_matching() — Same input → same output hash

### Integration Tests (3+ tests)
- test_full_pipeline_with_severity_audit() — End-to-end with all components
- test_multiple_findings_with_varying_severity() — Various severity tiers in same batch
- test_reproducibility_audit_after_delayed_verification() — Verify old batches

---

## Documentation Structure

### rule-catalog.md
```
# Clinical Contradiction Audit Engine - Rule Catalog

## Overview
- 18 deterministic rules across 6 FHIR resource types
- All rules deterministic (same input → same output)
- Evidence-backed findings with transparency fields

## Rule Index

### Condition Rules (4 rules)
- RULE-COND-001: Condition status contradiction
  - Severity Weight: 4
  - Example: Active condition with future onset
  - Evidence: {actual_status, onsetDateTime, current_date}

[... 17 more rules follow same format ...]

## Severity Weights
- Weight 5: Critical data integrity rules (RULE-COND-004)
- Weight 4: Patient safety risks (RULE-MED-001/004)
- Weight 3: Audit trail concerns (RULE-ENC-002)
- Weight 2: Data relevance (RULE-STALE-001)
- Weight 1: Informational (RULE-CARE-003)
```

### architecture-audit-engine.md
```
# Audit Engine Architecture

## System Design
- Rule Interface (ABC, immutable)
- Execution Orchestrator (sorted order, deterministic)
- Safety Boundary (keyword validation, audit logging)
- Evidence Extraction (complete transparency fields)
- Severity Scoring (deterministic algorithm)
- Audit Log (append-only, reproducibility)

## Data Flows
1. Batch Input → Rule Pack Loader → Execution Planner
2. Execution Plan → Orchestrator → Rule Execution
3. Rule Output → Evidence Extractor → Finding Assembly
4. Finding → Safety Validator → Severity Scorer
5. Scored Finding → Transparency Hydrator → Audit Log

## Reproducibility Model
- Input snapshot hash (SHA256)
- Output finding hash (SHA256)
- Archived rule pack version
- Verification: re-execute, compare hashes (≥95% pass)

## Design Patterns
- Rule Interface ABC for extensibility
- Factory pattern for rule instantiation
- Immutable Finding objects (frozen dataclass)
- Append-only audit log (integrity guarantee)
```

### deployment-guide.md
```
# Deployment Guide

## Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Required libraries: pydantic, PyYAML, pytest

## Installation
1. Clone repository
2. Create virtual environment
3. pip install -r requirements.txt
4. Configure PostgreSQL connection string in .env

## Database Setup
1. Run migrations: python scripts/migrate.py
2. Verify tables created: SELECT * FROM pg_tables WHERE schemaname='public'
3. Create indexes: python scripts/create_indexes.py

## Configuration
- Rule pack path: data/rule_packs/
- Stale threshold (default 5 years): config.yaml
- Safety keywords: config.yaml
- Reproducibility frequency: config.yaml

## Running Audits
- CLI: python -m module_1_data.cli audit --batch batch_001.json
- API: POST /api/audit {batch_id, cohort_ids}
- Output: findings.json, audit_log entries

## Monitoring
- Log files: logs/audit_engine.log
- Reproducibility reports: logs/reproducibility_audit_{date}.md
- Metrics: audit_log.findings_count, validated_findings_count
```

---

## Definition of Done

- [ ] All unit tests passing (15+ scenarios)
- [ ] Integration tests passing (reproducibility ≥95%)
- [ ] Rule catalog complete (all 18 rules documented)
- [ ] Architecture guide complete (design patterns, data flows)
- [ ] Deployment guide complete (setup, configuration, operations)
- [ ] Troubleshooting guide with common scenarios
- [ ] Documentation formatted and reviewed
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_005, task_009, task_012, task_014, task_015 (all must complete first)
- **Blocked By:** None
- **Related:** All prior tasks

---

**Effort:** 8 hours (4 hours testing, 4 hours documentation)  
**Owner:** QA/Test Engineer + Tech Lead (split)  
**Review Checklist:** Tests passing, documentation complete, rule catalog accurate, deployment guide clear
