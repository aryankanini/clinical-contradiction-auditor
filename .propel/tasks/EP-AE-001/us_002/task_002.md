---
taskId: task_002
epicId: EP-AE-001
parentStories: [us_002]
title: "Rule Pack Loader & YAML Deserializer"
priority: P0-Critical
status: PLANNED
estimatedHours: 5
---

# Task: Rule Pack Loader & YAML Deserializer

## Objective

Implement rule pack loading from YAML files, validation, versioning, and archive management. Enable deterministic rule orchestration by loading immutable rule packs.

---

## Acceptance Criteria Mapping

- **us_002 AC-1:** Load rule pack YAML files with schema validation
- **us_002 AC-2:** Validate semantic versioning and rule pack integrity
- **us_002 AC-3:** Archive previous rule pack versions for reproducibility
- **us_002 AC-4:** Persist rule pack metadata to database (via task_006)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/deterministic/rule_loader.py` | CREATE | YAML parser, validator, versioning, archive manager |
| `data/rule_packs/` | CREATE | Sample rule pack YAML templates |
| `module_2_audit_engine/models/rule_pack.py` | CREATE | Rule pack schema (pydantic models) |
| `tests/unit/test_rule_loader.py` | CREATE | Loader tests, validation tests, archive tests |

---

## Implementation Checklist

- [x] Define `RulePack` pydantic model (rules: List[Rule], version, metadata)
- [x] Implement YAML deserializer with error handling (parse errors → logged, traced)
- [x] Add schema validation using pydantic validators (version format, rule_id uniqueness)
- [x] Implement archive manager: previous versions stored with timestamp, filename convention
- [x] Create rule factory integration: loader instantiates rules via factory from pack
- [x] Implement versioning check: warn if new version > locked version in config
- [x] Write unit tests (≥4 scenarios: load valid, invalid, archive, version check)
- [x] Add logging: file load, parse success/failure, archive operations

---

## Technical Notes

- Use PyYAML 6.0+ for parsing; avoid unsafe load (use safe_load)
- Pydantic 2.0+ for schema validation
- Archive path convention: `archive/rule_pack-{version}-{timestamp}.yaml`
- Rule pack immutability: deserialize once, cache in memory for session
- Dependency injection: factory passed to loader for rule instantiation
- Logging: every file operation logged with context

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Invalid YAML syntax | Parser raises `RulePackParseError`, logs line number |
| Duplicate rule_id in pack | Validator raises `RuleDuplicateInPackError` |
| Version mismatch (new > locked) | Log WARNING; proceed if override flag set |
| Archive directory missing | Create directory automatically |
| Corrupted archive file | Log ERROR; archive operation skipped, continue |
| Empty rule pack | Valid (no rules); log WARN; emit empty execution plan |

---

## Definition of Done

- [ ] YAML deserializer functional (parse, validate, extract rules)
- [ ] Rule factory integration working (loader → factory → rule instances)
- [ ] Archive manager operational (create, list, retrieve previous versions)
- [ ] Versioning validation complete (semver check, locked version comparison)
- [ ] Logging comprehensive (parse, archive, version ops all logged)
- [ ] Unit tests pass (≥4 scenarios)
- [ ] No linting issues (black, flake8 pass)
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_001 (Rule Interface & Factory)
- **Blocked By:** None
- **Related:** task_006 (Database schema for rule_pack storage)

---

## Validation Strategy

- Unit test: Load valid rule pack, verify deserialization
- Unit test: Reject invalid rule pack (schema violation)
- Unit test: Archive previous version, verify retrieval
- Unit test: Version check (lock vs. new)
- Manual review: YAML parsing, error messages, logging clarity

---

## Testing Requirements

### Unit Tests
- `test_rule_loader_load_valid_pack()` — Load valid YAML, verify rules instantiated
- `test_rule_loader_invalid_yaml()` — Reject malformed YAML with clear error
- `test_rule_loader_duplicate_rule_id()` — Reject duplicate rule_id in pack
- `test_rule_archive_create_and_retrieve()` — Archive previous version, verify retrieval
- `test_rule_loader_version_check()` — Compare new vs. locked version, warn if needed

### Integration Tests
- (Deferred to task_005 — tested with orchestrator)

---

## External Resources

- PyYAML 6.0+: https://pyyaml.org/wiki/PyYAMLDocumentation
- Pydantic 2.0+: https://docs.pydantic.dev/latest/

---

**Effort:** 5 hours  
**Sequencing:** Second backend task (after task_001)  
**Owner:** Backend Engineer  
**Review Checklist:** Parser works, factory integration complete, archive functional, tests passing
