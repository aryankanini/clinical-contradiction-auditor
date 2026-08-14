# Task - TASK_003

## Requirement Reference

- **User Story:** US_003
- **Story Location:** .propel/context/tasks/EP-DATA-002/us_003/us_003.md
- **Acceptance Criteria:**
  - AC-01: Standardize normalization schema
  - AC-02: Preserve source traceability
  - AC-03: Represent invalid or missing values explicitly
- **Edge Cases:**
  - Multiple timestamps with different clinical meanings on the same resource
  - Status fields that vary by resource family semantics
  - References that resolve to external systems or unresolved local identifiers

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
| Backend | Python | 3.x | Shared normalization contracts align with the Python module structure |
| Library | Standard Library | Built-in | Contract modeling can start with dataclasses or typed objects |
| Database | N/A | N/A | Schema is application-level, not persistence-level, at this stage |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | No AI involvement |

---

## Task Overview

Define canonical normalized models for rule-critical status, timestamp, reference, and provenance fields so all downstream contradiction checks operate against a stable and traceable contract.

## Dependent Tasks

- TASK_002

## Impacted Components

- shared/models/
- shared/enums/
- module_1_data/ingestion/parser.py
- tests/unit/

## Implementation Plan

- Define normalized resource, field-state, and provenance models shared across the ingestion layer.
- Add enums or constants for normalization outcomes and field-state semantics.
- Ensure source identifiers and field-mapping metadata are retained in the contract.
- Add unit tests for model shape, explicit invalid-value representation, and traceability metadata.

## Current Project State

```text
.propel/context/tasks/EP-DATA-002/us_003/
  us_003.md
shared/
  models/
  enums/
module_1_data/
  ingestion/
    parser.py
tests/
  unit/
```

## Expected Changes

| Action | File Path | Description |
| --- | --- | --- |
| CREATE | shared/models/normalized_resource.py | Defines canonical normalized resource contracts |
| CREATE | shared/enums/normalization_state.py | Defines explicit normalization and field-state outcomes |
| MODIFY | module_1_data/ingestion/parser.py | Uses canonical models for staged normalization output |
| CREATE | tests/unit/test_normalized_models.py | Verifies model shape, traceability fields, and invalid-value representation |

## External References

- HL7 FHIR R4 field semantics for resource status, timestamps, and references

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Canonical models represent required, optional, derived, and invalid states explicitly
- [x] Source-to-normalized traceability fields are present and stable

## Implementation Checklist

- [x] Define canonical normalized models and provenance fields
- [x] Define explicit normalization state enums or constants
- [x] Update parser outputs to use shared normalized contracts
- [x] Add unit tests for schema and invalid-value representation
