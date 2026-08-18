---
taskId: task_007
epicId: EP-AE-002
parentStories: [us_005, us_006, us_007]
title: "Implement Contradiction Detection Rules"
priority: P1-High
status: IN_PROGRESS
estimatedHours: 8
---

# Task: Implement Contradiction Detection Rules

## Objective

Implement 18 deterministic contradiction detection rules across 5 FHIR resource types (Condition, Medication, Encounter, Procedure, Observation, CarePlan). Rules detect cross-resource inconsistencies with <100ms per-patient latency.

---

## Acceptance Criteria Mapping

- **us_005 AC-1:** Condition rules detect contradictions (4 rules: active/completed status, onsetDateTime conflicts)
- **us_006 AC-1:** Medication rules detect contradictions (5 rules: active/stopped status, effective dates)
- **us_007 AC-1:** Encounter/Procedure/Observation/CarePlan rules (9 rules)
- **us_005-007 AC-3:** <100ms per-patient execution time

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/rules/diagnosis_rules.py` | CREATE | Condition contradiction rules (4 rules) |
| `module_2_audit_engine/rules/medication_rules.py` | CREATE | Medication contradiction rules (5 rules) |
| `module_2_audit_engine/rules/encounter_rules.py` | CREATE | Encounter/Procedure/Observation/CarePlan rules (9 rules) |
| `data/rule_packs/contradiction_rules_v1.yaml` | CREATE | YAML definitions for all 18 rules |

---

## Rule Definitions

### Condition Rules (4 rules, 10 SP)
1. **RULE-COND-001:** Condition status contradiction
   - Contradiction: Resource has status="active" AND onsetDateTime > today (future onset)
   - Severity: HIGH
   - Evidence: {actual_status, onsetDateTime, today}

2. **RULE-COND-002:** Condition onset/abatement ordering
   - Contradiction: onsetDateTime > abatementDateTime
   - Severity: MEDIUM
   - Evidence: {onsetDateTime, abatementDateTime}

3. **RULE-COND-003:** Active condition with abatement date
   - Contradiction: status="active" AND abatementDateTime is set
   - Severity: MEDIUM
   - Evidence: {status, abatementDateTime}

4. **RULE-COND-004:** Entered-in-error with other status
   - Contradiction: status includes "error" AND other clinical entries exist for same code/patient
   - Severity: CRITICAL
   - Evidence: {status, conflicting_entries_count}

### Medication Rules (5 rules, 10 SP)
5. **RULE-MED-001:** Medication status contradiction
   - Contradiction: status="active" AND effectiveDateTime in past (inactive period)
   - Severity: HIGH
   - Evidence: {status, effectiveDateTime, current_date}

6. **RULE-MED-002:** Medication effective date ordering
   - Contradiction: effectiveStart > effectiveEnd
   - Severity: MEDIUM
   - Evidence: {effectiveStart, effectiveEnd}

7. **RULE-MED-003:** Stopped medication with active context
   - Contradiction: status="stopped" AND referenced by active CarePlan/MedicationRequest
   - Severity: MEDIUM
   - Evidence: {status, active_references_count, reference_ids}

8. **RULE-MED-004:** Dose contradiction
   - Contradiction: dose=0 OR dose < 0 (invalid dosage)
   - Severity: HIGH
   - Evidence: {dose, dose_unit}

9. **RULE-MED-005:** Duplicate medication entries
   - Contradiction: Multiple medication statements with same code, status, patient, overlapping dates
   - Severity: LOW
   - Evidence: {count, medication_ids, date_ranges}

### Encounter/Procedure/Observation/CarePlan Rules (9 rules, 10 SP)
10. **RULE-ENC-001:** Encounter period ordering
    - Contradiction: period.start > period.end
    - Severity: MEDIUM
    - Evidence: {period_start, period_end}

11. **RULE-ENC-002:** Encounter status contradiction
    - Contradiction: status="completed" AND period.end in future
    - Severity: HIGH
    - Evidence: {status, period_end, current_date}

12. **RULE-PROC-001:** Procedure performed date vs status
    - Contradiction: status="completed" AND performedDateTime is null OR empty
    - Severity: MEDIUM
    - Evidence: {status, performedDateTime}

13. **RULE-PROC-002:** Procedure period contradiction
    - Contradiction: performedPeriod.start > performedPeriod.end
    - Severity: MEDIUM
    - Evidence: {period_start, period_end}

14. **RULE-OBS-001:** Observation effective date vs status
    - Contradiction: status="final" AND effectiveDateTime > today (future observation)
    - Severity: MEDIUM
    - Evidence: {status, effectiveDateTime, current_date}

15. **RULE-OBS-002:** Observation value contradiction
    - Contradiction: value is null AND status != "cancelled"
    - Severity: HIGH
    - Evidence: {status, value_presence}

16. **RULE-CARE-001:** CarePlan status vs period
    - Contradiction: status="completed" AND period.end in future
    - Severity: MEDIUM
    - Evidence: {status, period_end, current_date}

17. **RULE-CARE-002:** CarePlan period contradiction
    - Contradiction: period.start > period.end
    - Severity: MEDIUM
    - Evidence: {period_start, period_end}

18. **RULE-CARE-003:** CarePlan with no activities
    - Contradiction: status="active" AND activity list is empty
    - Severity: LOW
    - Evidence: {status, activity_count}

---

## Implementation Checklist

- [x] Implement 4 Condition rules in `diagnosis_rules.py`
- [x] Implement 5 Medication rules in `medication_rules.py`
- [x] Implement 9 Encounter/Procedure/Observation/CarePlan rules in `encounter_rules.py`
- [x] Each rule inherits from RuleInterface (task_001)
- [x] Each rule implements execute(resources) → List[Finding]
- [x] Evidence extraction populated (field names, values, conflicts)
- [ ] Performance optimization: <100ms per patient (benchmark in task_009)
- [x] Add rule metadata (rule_id, version, category, severity_default)
- [x] Create YAML rule pack for all 18 rules
- [x] Document each rule with examples in docstrings

---

## Technical Notes

- Rule categorization: diagnosis, medication, encounter, procedure, observation, careplan
- Evidence payload: {field_name, actual_value, expected_value, conflict_description}
- Date comparisons: use timezone-aware UTC timestamps, handle null dates
- Status enum handling: vary by resource type (active, completed, cancelled, etc.)
- Cross-resource queries: Encounter rules may need to check related Procedures
- Performance: lazy evaluation where possible; pre-index status/effective date fields
- Exception handling: catch date parsing errors, log and emit Finding with status=PARTIAL

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Null status field | Skip status checks; log WARN; continue |
| Malformed date string | Catch DateTimeException; log WARN; emit Finding with status=PARSE_ERROR |
| Timezone mismatch (UTC vs local) | Standardize all dates to UTC in rules; handle in evidence |
| Missing resource in cross-resource rule | Skip that comparison; log at INFO level |
| Empty resources list | Return empty findings (valid) |
| Very large resource list (>10K) | Maintain <100ms target; optimize indexes in DB |

---

## Definition of Done

- [ ] All 18 rules implemented and functional
- [ ] Each rule has complete evidence extraction
- [ ] Rules inherit from RuleInterface correctly
- [ ] Performance <100ms per patient verified (benchmarked in task_009)
- [ ] YAML rule pack created and parseable
- [ ] Docstrings complete (Google style, examples included)
- [ ] No linting issues (black, flake8, mypy pass)
- [ ] Unit tests pass (handled in task_009)
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_001 (Rule Interface)
- **Blocked By:** None
- **Related:** task_008 (Evidence extraction uses these rules), task_009 (Integration tests)

---

## Validation Strategy

- Unit tests: Each rule tested with valid, edge case, and error inputs (3+ scenarios per rule)
- Performance: Benchmark all 18 rules with 1000-patient cohort, verify <100ms average
- Manual review: Evidence extraction complete, field names accurate, contradictions well-defined

---

## Testing Requirements

### Unit Tests (54+ tests)
- Per rule (3 tests × 18 = 54):
  - test_rule_contradicts_valid()
  - test_rule_accepts_valid()
  - test_rule_edge_case()

### Integration Tests (handled by task_009)
- End-to-end contradiction detection across all 18 rules

### Performance Tests (handled by task_009)
- Benchmark: <100ms per patient on 1000-patient cohort

---

## External Resources

- FHIR Condition: https://www.hl7.org/fhir/condition.html
- FHIR Medication: https://www.hl7.org/fhir/medication.html
- FHIR Encounter: https://www.hl7.org/fhir/encounter.html

---

**Effort:** 8 hours  
**Sequencing:** First backend task in EP-AE-002 (after EP-AE-001 complete)  
**Owner:** Backend Engineer  
**Review Checklist:** All 18 rules implemented, evidence complete, <100ms verified, YAML pack parseable, tests pass
