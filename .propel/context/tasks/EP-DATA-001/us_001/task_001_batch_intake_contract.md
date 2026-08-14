# Task - TASK_001

## Requirement Reference

- **User Story:** US_001
- **Story Location:** .propel/context/tasks/EP-DATA-001/us_001/us_001.md
- **Acceptance Criteria:**
  - AC-01: Accept supported batch shape
  - AC-02: Reject unsupported resource classes
  - AC-03: Fail malformed envelopes safely
- **Edge Cases:**
  - Empty batch submissions
  - Mixed valid and invalid records within one batch
  - Duplicate batch identifiers from the same source system
  - Payloads that omit one or more in-scope resource classes entirely

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
| Backend | Python | 3.x | FR-001 and repo module layout use Python ingestion modules under module_1_data |
| Library | Standard Library | Built-in | Contract and validation logic can start without third-party dependencies |
| Database | N/A | N/A | No persistence engine is implemented yet in the current scaffold |
| Frontend | N/A | N/A | No UI impact for intake contract definition |
| AI/ML | N/A | N/A | Story is deterministic and audit-bound |

---

## Task Overview

Define the initial batch intake contract for the ingestion layer so accepted FHIR payloads have a deterministic envelope, explicit supported resource classes, and safe failure semantics before staging or normalization begins.

## Dependent Tasks

- None

## Impacted Components

- module_1_data/pipeline.py
- module_1_data/ingestion/parser.py
- shared/models/
- tests/unit/

## Implementation Plan

- Define a canonical batch envelope and supported resource-type list for the six in-scope FHIR classes.
- Add deterministic validation logic for envelope structure, resource type membership, and malformed payload rejection.
- Define validation result objects that distinguish accepted, rejected, quarantined, and partial-ingest states.
- Add unit tests for supported payloads, malformed envelopes, unsupported resource classes, and empty batches.

## Current Project State

```text
.propel/context/tasks/EP-DATA-001/us_001/
  us_001.md
module_1_data/
  pipeline.py
  ingestion/
    parser.py
    csv_loader.py
    fhir_loader.py
shared/
  models/
tests/
  unit/
```

## Expected Changes

| Action | File Path | Description |
| --- | --- | --- |
| CREATE | shared/models/batch_contract.py | Defines accepted batch envelope and validation result models |
| MODIFY | module_1_data/ingestion/parser.py | Adds batch contract validation and safe failure handling |
| MODIFY | module_1_data/pipeline.py | Invokes contract validation before loader orchestration |
| CREATE | tests/unit/test_batch_contract.py | Covers supported, unsupported, malformed, and empty batch paths |

## External References

- HL7 FHIR R4 resource structure for the six in-scope resource types

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Contract validation rejects malformed and unsupported payloads deterministically

## Implementation Checklist

- [x] Define the accepted batch envelope and supported resource list
- [x] Implement deterministic contract validation in the ingestion parser
- [x] Surface accepted, rejected, and quarantined outcomes in pipeline metadata
- [x] Add unit tests for all three acceptance criteria and edge cases
