---
taskId: task_011
epicId: EP-AE-003
parentStories: [us_009, us_010]
title: "Implement Timeline & State Validation Rules"
priority: P2-Medium
status: PLANNED
estimatedHours: 7
---

# Task: Implement Timeline & State Validation Rules

## Objective

Implement 3 timeline and state lifecycle validation rules: stale state detection, temporal ordering, and state lifecycle validation. Handle DST/leap years, timezone conversions, and null dates.

---

## Acceptance Criteria Mapping

- **us_009 AC-1:** Stale state detection (5-year threshold configurable)
- **us_010 AC-1:** Temporal ordering validation (dates in logical sequence)
- **us_010 AC-2:** State lifecycle validation (allowed transitions)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/rules/timeline_rules.py` | CREATE | Stale state, temporal ordering, state lifecycle rules |
| `data/rule_packs/timeline_rules_v1.yaml` | CREATE | YAML definitions |

---

## Rule Definitions

### Timeline Rules (3 rules, 10 SP)

1. **RULE-STALE-001:** Stale State Detection
   - Contradiction: Resource status="active" AND last_updated < 5 years ago
   - Severity: MEDIUM
   - Evidence: {status, last_updated, current_date, age_years, threshold_years}
   - Handling: Configurable threshold (default 5 years); treat null dates as recent

2. **RULE-TEMPORAL-001:** Temporal Ordering Violation
   - Contradiction: Date sequences violate logical ordering
   - Examples: onsetDateTime > abatementDateTime, period.start > period.end
   - Severity: MEDIUM
   - Evidence: {field_names, actual_order, expected_order}
   - Handling: Handle DST/leap years; timezone-normalize to UTC

3. **RULE-LIFECYCLE-001:** State Lifecycle Validation
   - Contradiction: Impossible state transitions (e.g., cancelled → active)
   - Severity: MEDIUM
   - Evidence: {previous_status, current_status, transition_rule, allowed_transitions}
   - Handling: Define state machine per resource type; allow forward transitions only

---

## Implementation Checklist

- [ ] Define Timeline rule base class (inherit from RuleInterface)
- [ ] Implement stale state detection (configurable threshold, date arithmetic)
- [ ] Implement temporal ordering check (dates in logical sequence)
- [ ] Implement state lifecycle validation (state machine per resource type)
- [ ] Handle DST transitions (use pytz or zoneinfo for UTC normalization)
- [ ] Handle leap years (datetime library handles automatically)
- [ ] Handle null dates (treat as current date or skip check)
- [ ] Performance target: <50ms per patient for stale, <100ms for temporal
- [ ] Write docstrings and examples
- [ ] Create YAML rule pack for all 3 rules

---

## Technical Notes

- Date arithmetic: Python datetime + timedelta for year calculations
- Timezone handling: Normalize all dates to UTC before comparison
- DST: Use pytz.utc or zoneinfo.ZoneInfo for consistency
- State machine: Define as dict → Define allowed transitions
- Performance: Lazy evaluation; cache state machine on class init
- Edge case: Very old dates (pre-1900) may fail in some libraries

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Null status (stale check) | Skip stale check; log WARN; continue |
| Null date (temporal check) | Skip that date comparison; log WARN |
| DST transition boundary | Use UTC offset; test with March/October dates |
| Leap year (Feb 29) | Python datetime handles; test with 2024 leap day |
| Date string parsing error | Log WARN; emit Finding with status=PARSE_ERROR |
| Future dates (beyond 2100) | Log WARN; stale calculation handles correctly |

---

## Definition of Done

- [ ] All 3 rules implemented and functional
- [ ] DST/leap year handling verified via tests
- [ ] Stale threshold configurable (default 5 years)
- [ ] State machine defined for each resource type
- [ ] Performance <50ms stale, <100ms temporal verified
- [ ] YAML rule pack created and parseable
- [ ] Docstrings complete (examples included)
- [ ] No linting issues
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_001 (Rule Interface)
- **Blocked By:** None
- **Related:** task_012 (Integration tests)

---

**Effort:** 7 hours  
**Sequencing:** First backend task in EP-AE-003 (parallel with EP-AE-002)  
**Owner:** Backend Engineer  
**Review Checklist:** Rules implemented, DST/leap year handling verified, performance targets met, YAML pack parseable, tests pass
