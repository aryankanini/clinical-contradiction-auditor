# Task - TASK_004

## Requirement Reference

- **User Story:** US_004
- **Story Location:** .propel/context/tasks/EP-DATA-002/us_004/us_004.md
- **Acceptance Criteria:**
  - AC-01: Normalize statuses consistently
  - AC-02: Normalize timestamps and ordering fields
  - AC-03: Normalize reference linkages
- **Edge Cases:**
  - Conflicting timestamp fields on one resource
  - References pointing to records missing from the current batch
  - Multiple statuses where one source resource exposes both lifecycle and workflow state

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
| Backend | Python | 3.x | Normalization logic is implemented in the Python ingestion layer |
| Library | Standard Library | Built-in | Field mapping logic can start without introducing new libraries |
| Database | N/A | N/A | No persistence choice exists yet |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | Deterministic preprocessing only |

---

## Task Overview

Implement deterministic normalization logic for status, timestamp, and reference-linkage fields so downstream contradiction rules receive comparable inputs across all staged resources.

## Dependent Tasks

- TASK_003

## Impacted Components

- module_1_data/ingestion/parser.py
- module_1_data/pipeline.py
- shared/models/normalized_resource.py
- tests/unit/

## Implementation Plan

- Implement field-family-specific mappings from raw FHIR records into canonical status, timestamp, and linkage fields.
- Surface missing, ambiguous, or conflicting values as explicit normalization outcomes.
- Mark unresolved references for later completeness handling instead of hiding them.
- Add unit tests for status mapping, timestamp normalization, and linkage normalization.

## Current Project State

```text
.propel/context/tasks/EP-DATA-002/us_004/
  us_004.md
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
| MODIFY | module_1_data/ingestion/parser.py | Adds field-level status, timestamp, and linkage normalization logic |
| MODIFY | module_1_data/pipeline.py | Propagates normalized outputs and unresolved-reference markers |
| MODIFY | shared/models/normalized_resource.py | Extends canonical models as needed for rule-critical fields |
| CREATE | tests/unit/test_normalization_logic.py | Covers deterministic mapping and unresolved-reference behavior |

## External References

- HL7 FHIR R4 field semantics for lifecycle status, effective time, occurrence time, and resource references

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Status, timestamp, and reference normalization are deterministic
- [x] Unresolved or ambiguous values remain explicit in the normalized output

## Implementation Checklist

- [x] Implement deterministic status normalization
- [x] Implement deterministic timestamp normalization
- [x] Implement canonical reference-linkage normalization and unresolved markers
- [x] Add unit tests covering all three acceptance criteria
