---
taskId: task_005
epicId: EP-AE-001
parentStories: [us_001, us_002, us_003, us_004]
title: "Rule Engine Unit & Integration Tests"
priority: P0-Critical
status: COMPLETE
estimatedHours: 8
---

# Task: Rule Engine Unit & Integration Tests

## Objective

Develop comprehensive test suite for rule engine foundation (tasks 001-004). Verify rule interface contract, versioning, orchestration determinism, safety boundaries, and audit logging.

---

## Acceptance Criteria Mapping

- **us_001 AC-1-3:** Rule interface tests (immutability, contract, validation)
- **us_002 AC-1-2:** Rule pack versioning tests (load, archive, version validation)
- **us_003 AC-1-3:** Orchestrator tests (determinism, ordering, plan creation)
- **us_004 AC-1-3:** Safety validator tests (keyword detection, boundary enforcement, immutability)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `tests/unit/test_rule_interface.py` | CREATE | Factory, interface contract, immutability tests |
| `tests/unit/test_rule_loader.py` | CREATE | YAML parsing, validation, archive tests |
| `tests/unit/test_orchestrator.py` | CREATE | Determinism, ordering, plan builder tests |
| `tests/unit/test_safety_validator.py` | CREATE | Keyword detection, boundary enforcement tests |
| `tests/integration/test_rule_execution_end_to_end.py` | CREATE | Full pipeline: load → plan → execute → validate → audit |
| `tests/fixtures/sample_rules.yaml` | CREATE | Sample rule packs for testing |
| `tests/fixtures/conftest.py` | CREATE | Pytest fixtures (rule factory, loader, mock data) |

---

## Implementation Checklist

- [ ] Create pytest fixtures: RuleFactory, rule pack YAML samples, mock FHIR resources
- [ ] Implement unit test suite for RuleInterface (5+ factory tests, 3+ immutability tests)
- [ ] Implement unit test suite for RuleLoader (4+ load/validate/archive tests)
- [ ] Implement unit test suite for Orchestrator (3+ determinism, 2+ ordering, 2+ error handling)
- [ ] Implement unit test suite for SafetyValidator (5+ keyword detection, 3+ boundary enforcement)
- [ ] Create integration test: full pipeline from rule pack → execution → findings
- [ ] Add performance benchmark tests (per-rule time, total batch time)
- [ ] Configure test coverage reporting (pytest-cov, ≥80% target)
- [ ] Document test strategy in README

---

## Technical Notes

- Use pytest fixtures (conftest.py) for reusable rule factories, loaders, mock data
- Mock FHIR resources: simple objects with required fields (resourceType, id, status, dates)
- Test data: sample rule packs in YAML (minimal rules for fast tests, realistic rules for integration)
- Performance tests: time-series capture (plot graphs if >100 rules)
- Coverage: aim for ≥80% line coverage, 100% branch coverage on safety/orchestrator
- CI/CD integration: pytest runs on every commit, coverage reports to PR

---

## Edge Cases & Test Coverage

| Scenario | Test Case | Layer |
|----------|-----------|-------|
| Duplicate rule_id registration | test_rule_factory_duplicate_registration | Unit |
| Empty YAML file | test_rule_loader_empty_file | Unit |
| Invalid version string | test_rule_loader_invalid_version | Unit |
| Determinism (same input) | test_orchestrator_determinism | Unit |
| Rule execution order | test_orchestrator_execution_order | Unit |
| Rule throws exception | test_orchestrator_exception_handling | Unit |
| Keyword detection (diagnose) | test_safety_validator_keyword_diagnose | Unit |
| Safe finding passes | test_safety_validator_safe_finding | Unit |
| End-to-end pipeline | test_rule_execution_e2e | Integration |
| Performance <100ms | test_rule_execution_performance | Performance |

---

## Definition of Done

- [ ] All unit test files created and executable
- [ ] All integration test files created and executable
- [ ] Test coverage ≥80% overall, ≥90% for safety/orchestrator
- [ ] All tests pass (pytest run clean)
- [ ] No flaky tests (runs consistently)
- [ ] Fixtures documented (conftest.py comments)
- [ ] Test data realistic (sample rules, FHIR resources match spec)
- [ ] Performance benchmarks captured (timing reports)
- [ ] CI/CD integration configured (pytest on PR)
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_001-004 (Implementation tasks must complete first)
- **Blocked By:** None (can be written before implementation, then executed after)
- **Related:** task_006 (Database schema), task_009 (Contradiction detection tests build on this)

---

## Validation Strategy

- Automated: pytest run, coverage report, no failures
- Manual: Test coverage analysis, edge case review, performance benchmarks
- Peer review: Code review of test structure, fixture design, assertions

---

## Testing Requirements

### Unit Tests (30+ test cases total)

**RuleInterface Tests (8 tests)**
- test_rule_factory_register()
- test_rule_factory_lookup()
- test_rule_factory_duplicate_error()
- test_rule_factory_not_found_error()
- test_rule_metadata_frozen()
- test_rule_mutation_detected()
- test_rule_execute_signature()
- test_rule_invalid_version()

**RuleLoader Tests (5 tests)**
- test_rule_loader_valid_yaml()
- test_rule_loader_invalid_yaml()
- test_rule_loader_duplicate_rule_id()
- test_rule_archive_create()
- test_rule_archive_retrieve()

**Orchestrator Tests (7 tests)**
- test_orchestrator_determinism_run1_vs_run2()
- test_orchestrator_execution_order()
- test_execution_plan_creation()
- test_orchestrator_exception_handling()
- test_orchestrator_performance_metrics()
- test_orchestrator_empty_plan()
- test_orchestrator_large_plan_performance()

**SafetyValidator Tests (8 tests)**
- test_safety_keyword_detect_diagnose()
- test_safety_keyword_detect_treat()
- test_safety_keyword_detect_prescribe()
- test_safety_validator_safe_finding()
- test_safety_validator_reject_unsafe()
- test_finding_immutability()
- test_audit_log_append_only()
- test_audit_log_batch_entry()

### Integration Tests (3+ test cases)
- test_rule_execution_e2e() — Load YAML → Plan → Execute → Validate → Audit
- test_rule_execution_with_multiple_resources() — Execute against patient with Condition + Medication
- test_rule_execution_error_recovery() — One rule fails; batch continues with other rules

### Performance Tests (2+ test cases)
- test_rule_execution_performance_per_rule() — <100ms per patient average
- test_batch_performance_1000_patients() — Total time for 1000-patient cohort

---

## Test Data Specifications

### Sample Rule Pack (YAML)
```yaml
rule_pack_id: test-pack-001
version: 1.0.0
rules:
  - rule_id: rule_001
    rule_version: 1.0.0
    name: Test Rule 1
    category: test
  - rule_id: rule_002
    rule_version: 1.0.0
    name: Test Rule 2
    category: test
```

### Mock FHIR Resource
```python
{
  "resourceType": "Condition",
  "id": "cond-001",
  "status": "active",
  "code": {"coding": [{"code": "123", "system": "snomed"}]},
  "subject": {"reference": "Patient/p001"},
  "onsetDateTime": "2023-01-01T00:00:00Z"
}
```

---

## External Resources

- pytest documentation: https://docs.pytest.org/
- pytest-cov: https://pytest-cov.readthedocs.io/
- Python unittest.mock: https://docs.python.org/3.10/library/unittest.mock.html

---

**Effort:** 8 hours  
**Sequencing:** Last task in EP-AE-001 (after tasks 001-004, task_006)  
**Owner:** QA/Test Engineer  
**Review Checklist:** Coverage ≥80%, all tests pass, fixtures working, performance benchmarks captured, CI/CD ready
