---
taskId: task_003
epicId: EP-AE-001
parentStories: [us_003]
title: "Rule Execution Orchestrator & Plan Builder"
priority: P0-Critical
status: COMPLETE
estimatedHours: 8
---

# Task: Rule Execution Orchestrator & Plan Builder

## Objective

Implement deterministic rule execution orchestrator that loads rule packs, builds execution plans, and executes rules in canonical order (sorted by rule_id). Ensure reproducible, auditable execution with complete logging.

---

## Acceptance Criteria Mapping

- **us_003 AC-1:** Rule execution deterministic (same input → same output always)
- **us_003 AC-2:** Execution plan created before rule runs (logged for audit trail)
- **us_003 AC-3:** Rules executed in sorted order (sorted by rule_id, not load order)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/deterministic/orchestrator.py` | CREATE | Execution orchestrator, plan builder, execution controller |
| `module_2_audit_engine/models/execution_plan.py` | CREATE | Execution plan schema (rules, order, timestamps) |
| `module_2_audit_engine/deterministic/audit_log.py` | CREATE | Audit trail for execution (logged, persisted) |
| `tests/unit/test_orchestrator.py` | CREATE | Orchestrator tests, plan builder tests |

---

## Implementation Checklist

- [x] Define `ExecutionPlan` model (rules: List[Rule], execution_order: List[rule_id], timestamps)
- [x] Implement plan builder: load rule pack → extract rules → sort by rule_id → create plan
- [x] Implement orchestrator: iterate plan in order, execute each rule, collect findings
- [x] Create audit logger: log plan creation, rule execution start/end, findings emission
- [x] Implement result aggregator: combine findings from all rules, preserve rule_id lineage
- [x] Add performance metrics: capture execution time per rule, total batch time
- [x] Write unit tests (≥4 scenarios: determinism, ordering, plan creation, metrics)
- [x] Document execution flow in docstrings

---

## Technical Notes

- Rule execution sorted by rule_id (NOT load order) → determinism
- Fresh rule instance per batch (via factory) → no state accumulation
- Execution plan immutable after creation (log before execution)
- Audit log entries: {plan_id, rule_id, start_time, end_time, findings_count, status}
- Performance metrics enable benchmarking (task_009 performance tests)
- Dependency: rule_loader (task_002) must populate rule factory

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Rule execution throws exception | Catch, log ERROR, append finding with status=FAILED, continue |
| Rule_id parsing fails | Log WARN, skip rule (don't break batch) |
| Empty findings list from rule | Valid; log nothing, continue |
| Rule executes >500ms | Log WARN (slow); flag in metrics for investigation |
| Batch has zero rules | Valid; create empty plan, log INFO, return empty findings |
| Duplicate rule_id in pack (shouldn't happen but) | Detected in task_002; if reaches orchestrator, log ERROR, stop |

---

## Definition of Done

- [x] Orchestrator executes rules deterministically (same input → same output)
- [x] Execution plan created and logged before rules run
- [x] Rules execute in sorted order (rule_id canonical ordering)
- [x] Audit trail complete (plan, rule start/end, findings, metrics)
- [x] Error handling operational (exceptions caught, logged, batch continues)
- [x] Performance metrics captured (per-rule, total time)
- [x] Unit tests pass (≥4 determinism scenarios, ≥2 ordering scenarios)
- [x] No linting issues
- [x] Code review approved

---

## Dependencies

- **Blocking:** task_001 (Rule Interface), task_002 (Rule Loader)
- **Blocked By:** None
- **Related:** task_004 (Safety Validator wraps orchestrator), task_005 (Testing)

---

## Validation Strategy

- Unit test: Determinism (same input → same findings, identical order)
- Unit test: Ordering (verify rules execute in sorted rule_id order)
- Unit test: Plan creation (plan logged before execution)
- Unit test: Error handling (exception caught, batch continues)
- Manual review: Audit log entries, performance metrics

---

## Testing Requirements

### Unit Tests
- `test_orchestrator_determinism()` — Execute twice with same input, verify identical findings
- `test_orchestrator_execution_order()` — Verify rules execute in sorted rule_id order
- `test_execution_plan_builder()` — Build plan, verify rules in correct order, timestamps set
- `test_orchestrator_error_handling()` — Rule exception caught, batch continues, finding with FAILED status
- `test_orchestrator_performance_metrics()` — Per-rule timing captured, total time logged

### Integration Tests
- (Deferred to task_005 — integrated with safety validator)

---

## External Resources

- Python sorting: https://docs.python.org/3.10/howto/sorting.html
- Dataclass ordering: https://docs.python.org/3.10/library/dataclasses.html

---

**Effort:** 8 hours  
**Sequencing:** Third backend task (after task_001, task_002)  
**Owner:** Backend Engineer  
**Review Checklist:** Determinism verified, ordering correct, plan logged, error handling works, tests pass
