---
taskId: task_001
epicId: EP-AE-001
parentStories: [us_001]
title: "Implement Rule Interface Contract (ABC) & Factory"
priority: P0-Critical
status: PLANNED
estimatedHours: 6
---

# Task: Rule Interface Contract & Factory

## Objective

Establish the foundational Rule interface as an abstract base class (ABC) that enforces contract compliance for all deterministic contradiction detection rules. Implement a rule factory for instantiation and registration.

---

## Acceptance Criteria Mapping

- **us_001 AC-1:** Rule interface provides immutable execute() contract
- **us_001 AC-2:** Rule validation catches mutation violations at load time
- **us_001 AC-3:** Rule execution context is sealed (no side effects)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/deterministic/rule_interface.py` | CREATE | Rule ABC, metadata, execute() contract, validation, factory |
| `module_2_audit_engine/__init__.py` | MODIFY | Export RuleInterface, RuleFactory for public API |
| `tests/unit/test_rule_interface.py` | CREATE | Factory tests, immutability tests, validation tests |

---

## Implementation Checklist

- [x] Define `RuleInterface` ABC with execute(resources: List[Resource]) → List[Finding]
- [x] Add metadata fields: rule_id, version (semver), name, description, category
- [x] Implement immutability enforcement: frozen dataclass for metadata, validation in __init__
- [x] Create `RuleFactory` class for registration and instantiation
- [x] Implement rule validation: check for side-effects attempt (raise if detected)
- [x] Write factory unit tests (≥5 scenarios: registration, lookup, validation)
- [x] Add type hints throughout (Python 3.10+ compatible)
- [x] Document with docstrings (Google style)

---

## Technical Notes

- Use Python `dataclasses.dataclass(frozen=True)` for metadata immutability
- Leverage `abc.ABC` and `@abstractmethod` for contract enforcement
- Rule validation should introspect method signature and flag if input list mutation detected
- Factory pattern enables dynamic rule loading in task_002 (Rule Loader)
- Namespace rules by category (e.g., diagnosis, medication, timeline) in factory

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Duplicate rule_id registration | Factory raises `RuleDuplicateError`; logs conflict |
| Malformed rule (missing execute) | Factory raises `RuleContractError` at instantiation time |
| Version string invalid | Validation raises `RuleVersionError` during __init__ |
| Empty resources list | Accept empty list; execute() returns empty findings (valid) |
| Rule with non-frozen metadata | Validation detects, raises `RuleImmutabilityError` |

---

## Definition of Done

- [ ] RuleInterface ABC fully defined with all contract methods
- [ ] Factory implements full lifecycle (register, lookup, instantiate)
- [ ] All validation checks operational and unit tested
- [ ] Type hints complete (mypy --strict clean)
- [ ] Docstrings complete (Google style, ≥90 lines)
- [ ] Unit tests pass (pytest, ≥5 factory scenarios, ≥3 validation scenarios)
- [ ] No linting issues (black, flake8 pass)
- [ ] Code review approved before advancing to task_002

---

## Dependencies

- **Blocking:** None (foundational)
- **Blocked By:** None
- **Related:** task_002 (Rule Loader uses factory)

---

## Validation Strategy

- Unit test: Factory registration & lookup (4 scenarios)
- Unit test: Rule immutability enforcement (3 scenarios)
- Unit test: Validation error paths (2 scenarios)
- Manual review: Docstrings, type hints, immutability guarantees

---

## Testing Requirements

### Unit Tests
- `test_rule_factory_register()` — Register rule, verify in registry
- `test_rule_factory_lookup()` — Lookup registered rule, confirm identity
- `test_rule_factory_duplicate_registration()` — Reject duplicate rule_id
- `test_rule_interface_contract()` — Verify execute() signature
- `test_rule_metadata_frozen()` — Confirm metadata immutability
- `test_rule_validation_detects_mutation()` — Catch input mutation attempts

### Integration Tests
- (Deferred to task_005 — Rule Engine end-to-end tests)

---

## External Resources

- Python ABC documentation: https://docs.python.org/3.10/library/abc.html
- Immutability patterns: https://docs.python.org/3.10/library/dataclasses.html#frozen-instances

---

**Effort:** 6 hours  
**Sequencing:** First backend task (follow DB schema task_006)  
**Owner:** Backend Engineer  
**Review Checklist:** Contract defined, factory working, validation complete, tests passing
