---
taskId: task_009
epicId: EP-AE-002
parentStories: [us_005, us_006, us_007, us_008]
title: "Contradiction Detection Integration Tests & Benchmarks"
priority: P1-High
status: IN_PROGRESS
estimatedHours: 8
---

# Task: Contradiction Detection Integration Tests & Benchmarks

## Objective

Develop comprehensive integration test suite for contradiction detection (tasks 007-008). Verify all 18 rules execute correctly, evidence extracts completely, and performance meets <100ms per-patient target across 1000-patient cohorts.

---

## Acceptance Criteria Mapping

- **us_005-008 (all AC):** Integration tests verify all rules, evidence, and performance

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `tests/integration/test_contradiction_detection_pipeline.py` | CREATE | E2E tests for all 18 rules |
| `tests/fixtures/fhir_test_data.py` | CREATE | FHIR resource fixtures (Conditions, Medications, etc.) |
| `tests/performance_benchmarks/benchmark_contradiction_rules.py` | CREATE | Performance benchmark suite |
| `tests/reports/contradiction_benchmark_report.md` | CREATE | Benchmark results and analysis |

---

## Implementation Checklist

- [x] Create FHIR test fixtures (realistic Condition, Medication, Encounter, etc. resources)
- [x] Implement integration test suite (54+ tests: 3 per rule × 18 rules)
- [x] Test each rule with valid, contradicted, and edge-case inputs
- [x] Verify evidence extraction completeness (≥90% for each finding)
- [ ] Test cross-resource contradictions (e.g., active medication in completed encounter)
- [x] Implement performance benchmarks (1000-patient cohort, per-rule timing)
- [x] Capture timing reports (CSV with rule_id, avg_time_ms, p99_time_ms)
- [x] Document results in markdown report (analysis, recommendations)
- [x] Validate <100ms target across all rules

---

## Test Scenarios (54+ tests)

### Per-Rule Test Template (3 tests × 18 = 54 tests)
1. **test_rule_XXX_valid()** — Input has no contradiction; verify finding NOT emitted
2. **test_rule_XXX_contradicts()** — Input violates rule; verify Finding emitted with correct evidence
3. **test_rule_XXX_edge_case()** — Edge case (null dates, empty lists, etc.); verify handled gracefully

### Cross-Resource Tests (5+ tests)
- test_contradiction_medication_in_active_encounter() — Medication status inconsistent with encounter status
- test_contradiction_procedure_without_encounter() — Procedure has no corresponding encounter
- test_contradiction_observation_outside_encounter() — Observation date outside encounter period
- test_contradiction_careplan_with_stopped_medication() — Active CarePlan references stopped medication
- test_multiple_contradictions_single_patient() — Multiple findings for one patient in one batch

### Performance Tests (5+ tests)
- test_performance_100_patients() — <100ms total, verify per-rule averages
- test_performance_1000_patients() — Larger cohort, verify linear scaling
- test_performance_per_rule_distribution() — Identify slowest rules, recommend optimization
- test_performance_concurrent_execution() — Parallel rule execution if applicable
- test_performance_memory_usage() — Memory footprint for large cohorts

---

## Technical Notes

- FHIR fixtures: Use realistic but minimal examples (avoid bloated test data)
- Benchmark runs: 3 iterations per cohort size; report mean, min, max, p99
- Timing measurement: Use perf_counter() or Python's timeit module
- Cohort sizes: 100, 500, 1000 patients; plot scaling curve
- Results storage: CSV for data analysis, markdown for human reading
- Regression detection: Store baseline benchmarks; alert if regression >10%

---

## Edge Cases in Test Data

| Resource Type | Edge Case | Test Data |
|---------------|-----------|-----------|
| Condition | Null onsetDateTime | {"status": "active", "onsetDateTime": null} |
| Condition | Future onset | {"status": "active", "onsetDateTime": "2050-01-01T00:00:00Z"} |
| Medication | Zero dose | {"dose": 0, "doseUnit": "mg"} |
| Medication | Negative dose | {"dose": -5, "doseUnit": "mg"} |
| Encounter | Invalid period | {"period": {"start": "2024-12-31T00:00:00Z", "end": "2024-01-01T00:00:00Z"}} |
| Procedure | Null performedDateTime | {"status": "completed", "performedDateTime": null} |
| Observation | Future effectiveDateTime | {"status": "final", "effectiveDateTime": "2050-01-01T00:00:00Z"} |
| CarePlan | Empty activity list | {"status": "active", "activity": []} |

---

## Definition of Done

- [ ] All 54+ rule tests passing
- [ ] All cross-resource tests passing
- [ ] Performance <100ms per-patient verified
- [ ] Benchmark report generated (CSV + markdown)
- [ ] No regression from baseline (if baseline exists)
- [ ] Test fixtures realistic and well-documented
- [ ] No flaky tests (consistent results across runs)
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_005 (Unit tests provide fixtures), task_007-008 (Implementation complete)
- **Blocked By:** None
- **Related:** task_005 (Reuse fixtures), task_012 (Timeline tests follow similar pattern)

---

## Validation Strategy

- Automated: pytest run, coverage report, performance benchmarks
- Manual: Benchmark results analysis, regression detection
- Peer review: Test coverage, edge case completeness

---

## Test Data Specifications

### FHIR Condition Fixture
```json
{
  "resourceType": "Condition",
  "id": "cond-001",
  "status": "active",
  "code": {"coding": [{"code": "123", "system": "snomed"}]},
  "subject": {"reference": "Patient/p001"},
  "onsetDateTime": "2023-06-15T10:30:00Z",
  "abatementDateTime": "2023-12-15T10:30:00Z"
}
```

### FHIR Medication Fixture
```json
{
  "resourceType": "Medication",
  "id": "med-001",
  "code": {"coding": [{"code": "456", "system": "rxnorm"}]},
  "status": "active",
  "form": {"coding": [{"code": "tablet"}]}
}
```

### Benchmark Results Format (CSV)
```
rule_id,rule_name,cohort_size,iterations,avg_time_ms,min_time_ms,max_time_ms,p99_time_ms,status
RULE-COND-001,Condition status contradiction,100,3,12.3,11.8,13.1,13.0,PASS
RULE-COND-001,Condition status contradiction,1000,3,123.4,122.1,125.2,125.0,PASS
```

---

## External Resources

- pytest documentation: https://docs.pytest.org/
- Python timeit: https://docs.python.org/3.10/library/timeit.html
- FHIR examples: https://www.hl7.org/fhir/examples.html

---

**Effort:** 8 hours  
**Sequencing:** Last task in EP-AE-002 (after task_007-008, parallel with task_010)  
**Owner:** QA/Test Engineer  
**Review Checklist:** Coverage complete, <100ms verified, benchmarks captured, no flaky tests, performance baseline established
