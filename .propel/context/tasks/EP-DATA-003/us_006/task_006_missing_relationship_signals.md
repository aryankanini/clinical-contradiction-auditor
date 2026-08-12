# Task - TASK_006

## Requirement Reference

- **User Story:** US_006
- **Story Location:** .propel/context/tasks/EP-DATA-003/us_006/us_006.md
- **Acceptance Criteria:**
  - AC-01: Mark generic incompleteness separately
  - AC-02: Mark rule-expected relationship gaps
  - AC-03: Preserve audit-only boundaries in validation output
- **Edge Cases:**
  - Relationship rules change across rule-pack versions
  - A record is linked but the linked resource is unsupported for the current rule
  - Multiple rule families interpret the same absent relationship differently

---

## Design References

| Reference Type | Value |
| --- | --- |
| **UI Impact** | No |
| **Figma URL** | N/A |
| **Wireframe Status** | N/A |
| **Wireframe Type** | N/A |
| **Wireframe Path/URL** | N/A |
| **Screen Spec** | N/A |
| **UXR Requirements** | N/A |
| **Design Tokens** | N/A |

---

## AI References

| Reference Type | Value |
| --- | --- |
| **AI Impact** | No |
| **AIR Requirements** | N/A |
| **AI Pattern** | N/A |
| **Prompt Template Path** | N/A |
| **Guardrails Config** | N/A |
| **Model Provider** | N/A |

---

## Mobile References

| Reference Type | Value |
| --- | --- |
| **Mobile Impact** | No |
| **Platform Target** | N/A |
| **Min OS Version** | N/A |
| **Mobile Framework** | N/A |

---

## Applicable Technology Stack

| Layer | Technology | Version | Justification |
| --- | --- | --- | --- |
| Backend | Python | 3.x | Governed signal emission belongs to the deterministic ingestion path |
| Library | Standard Library | Built-in | Rule-readiness signal logic can begin without new external libraries |
| Database | N/A | N/A | Signal semantics come before persistence choice |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | No AI involvement |

---

## Task Overview

Emit governed missing-relationship signals that distinguish rule-expected relationship gaps from generic incompleteness, while preserving audit-only wording and keeping rule interpretation explicit.

## Dependent Tasks

- TASK_005

## Impacted Components

- module_1_data/pipeline.py
- shared/models/validation_state.py
- module_2_audit_engine/rules/
- tests/unit/

## Implementation Plan

- Define a signal structure for rule-expected missing relationships separate from generic validation outcomes.
- Add mapping logic from validation state into governed missing-relationship signals when a rule expectation exists.
- Preserve audit-only wording and avoid universal clinical assertions in emitted signals.
- Add unit tests for generic incompleteness, governed missing-relationship signals, and version-sensitive rule semantics.

## Current Project State

```text
.propel/context/tasks/EP-DATA-003/us_006/
  us_006.md
module_1_data/
  pipeline.py
shared/
  models/
module_2_audit_engine/
  rules/
tests/
  unit/
```

## Expected Changes

| Action | File Path | Description |
| --- | --- | --- |
| MODIFY | shared/models/validation_state.py | Extends validation models with governed missing-relationship signal structures |
| MODIFY | module_1_data/pipeline.py | Emits governed signals only when explicit rule expectations are present |
| MODIFY | module_2_audit_engine/rules/timeline_rules.py | Documents or consumes rule-expected relationship signal shape as needed |
| CREATE | tests/unit/test_missing_relationship_signals.py | Verifies separation between generic incompleteness and governed signals |

## External References

- Governed rule semantics from the project specification for expected missing relationships

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Generic incompleteness is not emitted as a governed missing-relationship signal
- [x] Governed signals remain audit-only and rule-bound

## Implementation Checklist

- [x] Define governed missing-relationship signal structure
- [x] Add logic to emit signals only when explicit rule expectations exist
- [x] Preserve audit-only semantics in emitted validation outputs
- [x] Add unit tests for generic versus governed cases
