---
taskId: task_012
epicId: EP-AE-003
parentStories: [us_009, us_010]
title: "Timeline Rules Unit & Integration Tests"
priority: P2-Medium
status: PLANNED
estimatedHours: 6
---

# Task: Timeline Rules Unit & Integration Tests

## Objective

Develop test suite for timeline and state validation rules (task_011). Verify stale detection, temporal ordering, and state lifecycle validation across edge cases (DST, leap years, null dates).

---

## Acceptance Criteria Mapping

- **us_009-010 (all AC):** Integration tests verify all timeline rules, edge cases

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `tests/unit/test_timeline_rules.py` | CREATE | Unit tests for stale, temporal, lifecycle rules |
| `tests/integration/test_timeline_validation_pipeline.py` | CREATE | E2E tests |

---

## Test Scenarios (15+ tests)

### Stale State Tests (5 tests)
- test_stale_detection_active_5years_old() — Detect stale resource
- test_stale_detection_recent_active() — No detection for recent resource
- test_stale_detection_null_date() — Skip null date gracefully
- test_stale_threshold_configurable() — Verify threshold override

### Temporal Ordering Tests (5 tests)
- test_temporal_ordering_valid() — Dates in correct sequence
- test_temporal_ordering_invalid() — Detect date reversal
- test_temporal_ordering_dst_boundary() — Handle DST transition
- test_temporal_ordering_leap_year() — Handle Feb 29
- test_temporal_ordering_null_dates() — Skip null dates

### State Lifecycle Tests (5 tests)
- test_lifecycle_valid_transition() — Allow forward-only transitions
- test_lifecycle_invalid_transition() — Reject impossible transitions
- test_lifecycle_cancelled_to_active() — Detect invalid resurrections
- test_lifecycle_null_status() — Handle missing status

### Integration Tests (3+ tests)
- test_timeline_pipeline_e2e() — Full stale + temporal + lifecycle checks
- test_timeline_multiple_findings() — Multiple timeline findings per patient

---

## Edge Case Coverage

| Edge Case | Test |
|-----------|------|
| DST Spring Forward (2:00 AM → 3:00 AM) | test_temporal_ordering_dst_spring |
| DST Fall Back (2:00 AM → 1:00 AM) | test_temporal_ordering_dst_fall |
| Leap Year (Feb 29) | test_temporal_ordering_leap_year_feb29 |
| Pre-1900 dates | test_temporal_ordering_historical_dates |
| Timezone mismatch (UTC vs EST) | test_temporal_ordering_timezone_conversion |

---

**Effort:** 6 hours  
**Owner:** QA/Test Engineer  
**Review Checklist:** Coverage complete, DST/leap year edge cases tested, performance targets met, no flaky tests
