# Task - TASK_002

## Requirement Reference

- **User Story:** US_002
- **Story Location:** .propel/context/tasks/EP-DATA-001/us_002/us_002.md
- **Acceptance Criteria:**
  - AC-01: Load all supported resource families
  - AC-02: Support partial family presence
  - AC-03: Capture loader-level failure status
- **Edge Cases:**
  - Unknown extensions inside otherwise supported FHIR resources
  - Repeated resource identifiers across families
  - Batches that exceed the expected family count for one patient cohort

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
| Backend | Python | 3.x | Loader implementation belongs to module_1_data Python source files |
| Library | Standard Library | Built-in | Initial loader routing can be implemented without new external libraries |
| Database | N/A | N/A | Staging is in-memory or file-oriented until persistence is chosen |
| Frontend | N/A | N/A | No UI impact |
| AI/ML | N/A | N/A | Deterministic ingestion story only |

---

## Task Overview

Implement resource-family loaders and orchestration so valid batches route each supported FHIR family into deterministic staging outputs while preserving source identifiers and loader-level outcome counts.

## Dependent Tasks

- TASK_001

## Impacted Components

- module_1_data/pipeline.py
- module_1_data/ingestion/fhir_loader.py
- module_1_data/ingestion/csv_loader.py
- shared/models/
- tests/unit/

## Implementation Plan

- Define a loader interface and a dispatch map for the six in-scope resource families.
- Implement family-specific staging logic that preserves identifiers and resource types.
- Support partial-family batches without converting absence into parser failure.
- Capture loader-level success and failure counts in ingest-run metadata.
- Add unit tests for full-family, partial-family, and loader-failure scenarios.

## Current Project State

```text
.propel/context/tasks/EP-DATA-001/us_002/
  us_002.md
module_1_data/
  pipeline.py
  ingestion/
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
| MODIFY | module_1_data/ingestion/fhir_loader.py | Adds family-based loader dispatch and staged record construction |
| MODIFY | module_1_data/pipeline.py | Orchestrates loader execution and aggregates loader outcomes |
| CREATE | shared/models/staged_resource.py | Defines staged resource structures and loader result metadata |
| CREATE | tests/unit/test_resource_loaders.py | Covers full, partial, and failure-path loader execution |

## External References

- HL7 FHIR R4 resource type definitions for Conditions, Medications, Procedures, Encounters, Observations, and CarePlans

## Build Commands

- Python test command to be defined once the backend dependency manifest exists

## Implementation Validation Strategy

- [x] Unit tests pass
- [x] All supported resource families route to the correct loader
- [x] Partial-family batches remain processable and observable

## Implementation Checklist

- [x] Implement loader dispatch for the six in-scope resource families
- [x] Preserve source identifiers and resource type labels in staged outputs
- [x] Record loader-level success and failure counts
- [x] Add unit tests for supported, partial, and failed loader paths
