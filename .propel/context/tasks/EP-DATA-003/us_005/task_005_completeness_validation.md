# Task - TASK_005

## Requirement Reference

- **User Story:** US_005
- **Story Location:** .propel/context/tasks/EP-DATA-003/us_005/us_005.md
- **Acceptance Criteria:**
  - AC-01: Detect unresolved cross-resource links
  - AC-02: Detect incomplete rule-critical fields
  - AC-03: Separate validation state from contradiction state
- **Edge Cases:**
  - A record is complete by schema but unusable for one specific rule family
  - A reference resolves to multiple candidate records
  - One batch contains both complete and incomplete records for the same patient context

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
| Backend | Python | 3.x | Completeness checks belong to the Python ingestion pipeline |
| Library | Standard Library | Built-in | Validation rules can start in application code without external dependencies |
| Database | N/A | N/A | Validation state is modeled before persistence is chosen |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | Deterministic validation only |

---

## Task Overview

Add a completeness and linkage-validation layer that classifies unresolved links and incomplete rule-critical data before contradiction evaluation, while keeping these signals distinct from contradiction findings.

## Dependent Tasks

- TASK_004

## Impacted Components

- module_1_data/pipeline.py
- module_1_data/ingestion/parser.py
- shared/models/
- tests/unit/

## Implementation Plan

- Define validation result models for unresolved links, incomplete records, and rule-readiness status.
- Implement linkage checks against normalized references and completeness checks against rule-critical field classes.
- Keep validation outputs separate from contradiction semantics in both naming and status values.
- Add unit tests for unresolved links, incomplete records, mixed batch states, and non-contradiction output behavior.

## Current Project State

```text
.propel/context/tasks/EP-DATA-003/us_005/
  us_005.md
module_1_data/
  pipeline.py
  ingestion/
    parser.py
shared/
  models/
tests/
  unit/
```

## Expected Changes

| Action | File Path | Description |
| --- | --- | --- |
| CREATE | shared/models/validation_state.py | Defines unresolved-link, incompleteness, and rule-readiness states |
| MODIFY | module_1_data/ingestion/parser.py | Computes linkage and completeness validation outcomes |
| MODIFY | module_1_data/pipeline.py | Propagates validation state separately from contradiction evaluation |
| CREATE | tests/unit/test_completeness_validation.py | Covers unresolved-link, incomplete-field, and mixed-state scenarios |

## External References

- HL7 FHIR R4 reference semantics for cross-resource links

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Unresolved-link and incompleteness states are emitted deterministically
- [x] Validation states are not mislabeled as contradiction findings

## Implementation Checklist

- [x] Define explicit validation-state models
- [x] Implement linkage validation against normalized references
- [x] Implement completeness checks for rule-critical fields
- [x] Add unit tests for unresolved, incomplete, and mixed batch cases
