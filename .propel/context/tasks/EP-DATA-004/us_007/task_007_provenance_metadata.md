# Task - TASK_007

## Requirement Reference

- **User Story:** US_007
- **Story Location:** .propel/context/tasks/EP-DATA-004/us_007/us_007.md
- **Acceptance Criteria:**
  - AC-01: Record ingest-run provenance
  - AC-02: Record normalization and validation outcomes
  - AC-03: Preserve immutable provenance facts
- **Edge Cases:**
  - Reprocessing the same batch with a newer rule-pack version later in the pipeline
  - Partial retry of records from a previously failed batch
  - Source system identifiers that are non-unique without extra provenance fields

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
| Backend | Python | 3.x | Provenance metadata is produced by the Python ingestion pipeline |
| Library | Standard Library | Built-in | Initial provenance model and serialization can start without external dependencies |
| Database | N/A | N/A | Storage target is not yet selected in the scaffold |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | Deterministic audit-trail task only |

---

## Task Overview

Persist ingest-run provenance metadata that captures source batch identity, processing counts, normalization outcomes, and validation outcomes as immutable facts for downstream auditability.

## Dependent Tasks

- TASK_005

## Impacted Components

- module_1_data/pipeline.py
- shared/models/
- tests/unit/

## Implementation Plan

- Define an ingest provenance model that captures batch identity, counts, processing status, and validation summaries.
- Persist provenance metadata at the end of each ingest run in a stable artifact shape.
- Protect provenance from later mutation by downstream reasoning or resolution workflows.
- Add unit tests for full success, partial processing, and retry-sensitive provenance scenarios.

## Current Project State

```text
.propel/context/tasks/EP-DATA-004/us_007/
  us_007.md
module_1_data/
  pipeline.py
shared/
  models/
tests/
  unit/
```

## Expected Changes

| Action | File Path | Description |
| --- | --- | --- |
| CREATE | shared/models/ingest_provenance.py | Defines immutable ingest-run provenance structures |
| MODIFY | module_1_data/pipeline.py | Builds and persists provenance metadata after ingest execution |
| CREATE | tests/unit/test_ingest_provenance.py | Verifies success, partial-processing, and retry-related provenance outcomes |
| MODIFY | module_1_data/ingestion/parser.py | Supplies normalization and validation summaries needed by provenance |

## External References

- Audit-log and reproducibility requirements from the project specification

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] Provenance captures batch identity, counts, and validation outcomes deterministically
- [x] Provenance records remain immutable after creation

## Implementation Checklist

- [x] Define immutable ingest provenance models
- [x] Persist provenance metadata at ingest-run completion
- [x] Capture normalization and validation summaries in provenance
- [x] Add unit tests for success, partial, and retry-sensitive cases
