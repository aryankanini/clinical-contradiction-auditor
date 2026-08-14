# Epics

## Scope

This artifact decomposes only the data-ingestion layer for the AI-Powered Clinical Data Integrity Auditor. It uses [.propel/context/docs/brd.md](.propel/context/docs/brd.md), [.propel/context/docs/spec.md](.propel/context/docs/spec.md), and [.propel/context/docs/codeanalysis.md](.propel/context/docs/codeanalysis.md) as source artifacts.

The scope covers ingesting batch FHIR patient records, normalizing cross-resource fields, enforcing rule-ready completeness checks, and preserving ingestion provenance required by the downstream deterministic audit workflow. It does not cover contradiction rule execution, AI explanation, API/UI delivery, or resolution workflow behavior except where ingestion artifacts must support them.

## Epic Catalog

### EP-DATA-001: FHIR Batch Intake Foundation

Goal:
Establish a reliable ingestion entry point for batch FHIR patient records across the six in-scope resource types: Conditions, Medications, Procedures, Encounters, Observations, and CarePlans.

Business value:
Creates the minimum executable backbone for the product by turning raw patient-record batches into a controlled input surface for deterministic auditing.

Parent requirements:

- FR-001
- FR-011

Included capabilities:

- Define the batch ingestion contract for accepted FHIR payload structure and supported resource classes.
- Implement resource-family loaders under `module_1_data/ingestion` for the in-scope FHIR resources.
- Reject or quarantine malformed payloads without producing diagnostic or treatment-oriented output.
- Emit ingest-run metadata that identifies batch source, record counts, and processing status.

Definition of done:

- A batch containing the six in-scope FHIR resource types can be ingested into a canonical staging structure.
- Unsupported or malformed input paths fail safely and remain audit-only in their responses.
- Ingest-run metadata is persisted for downstream traceability.

Dependencies:

- Shared domain models for staged FHIR resources must be defined first.
- Sample input bundles are required because the current repository has no populated data fixtures.

### EP-DATA-002: Canonical Resource Normalization

Goal:
Normalize the status, timestamp, and reference-linkage fields needed for cross-resource consistency checks so the deterministic engine receives stable, comparable inputs.

Business value:
Reduces false positives and brittle rule logic by converting heterogeneous FHIR payloads into a single canonical representation before contradiction evaluation begins.

Parent requirements:

- FR-002

Included capabilities:

- Define canonical normalized models for status fields, time fields, references, and provenance markers.
- Implement normalization logic for each in-scope resource family.
- Standardize missing, partial, and invalid values into explicit ingestion outcomes rather than silent coercion.
- Preserve source-to-normalized field mappings so audit evidence can trace back to original records.

Definition of done:

- All in-scope resources are transformed into a shared normalized model with explicit linkage fields.
- Timestamp, status, and reference normalization rules are deterministic and testable.
- Source-to-normalized mappings are retained for evidence and replay use.

Dependencies:

- EP-DATA-001
- A canonical finding and evidence schema is needed to avoid rework in downstream modules.

### EP-DATA-003: Linkage Validation and Completeness Guards

Goal:
Validate that ingested records are sufficiently complete and internally linkable for cross-resource contradiction rules, while clearly separating incomplete data from true contradiction findings.

Business value:
Prevents the deterministic engine from confusing missing data with contradictory data and creates a cleaner operational queue for remediation.

Parent requirements:

- FR-002
- FR-005
- FR-011

Included capabilities:

- Detect missing required references, unresolved cross-resource links, and incomplete ingest payloads.
- Mark records and batches with explicit completeness status for downstream rule handling.
- Route rule-expected missing relationships into rule-ready signals without asserting universal clinical truth.
- Ensure ingestion guardrails do not emit diagnostic conclusions or alter clinical intent.

Definition of done:

- Incomplete or unlinked records are identified before deterministic contradiction evaluation.
- Rule-expected missing relationship conditions are represented distinctly from generic ingest failures.
- The ingest layer outputs enough structured linkage status for downstream rule packs to decide whether to evaluate, skip, or flag a case.

Dependencies:

- EP-DATA-002
- Governance on what counts as rule-expected missing relationships must be available from the rule-management path.

### EP-DATA-004: Ingestion Traceability and Replay Artifacts

Goal:
Preserve the provenance, evidence pointers, and replayable ingest artifacts required for reproducible audits and downstream transparency fields.

Business value:
Supports compliance review, reproducibility, and confidence in audit results by ensuring each downstream finding can be reconstructed from stored ingest artifacts.

Parent requirements:

- FR-006
- FR-012

Included capabilities:

- Persist ingest provenance for source batch, record counts, normalization outcomes, and linkage-validation outcomes.
- Store record identifiers and field-level mappings needed to reconstruct evidence packets later.
- Capture deterministic ingest warnings and partial-processing outcomes without losing replay fidelity.
- Define retention-ready artifact boundaries so downstream audit logs can reference immutable ingestion facts.

Definition of done:

- A sampled ingest run can be replayed or reconstructed from stored artifacts without depending on raw transient process memory.
- Downstream finding generation has access to stable record identifiers and provenance references.
- Ingestion transparency artifacts are compatible with the broader audit-log design in the specification.

Dependencies:

- EP-DATA-001
- EP-DATA-002
- Repository-wide logging and artifact persistence conventions must be established because the current codebase has no runtime implementation.

## Traceability Summary

| Epic ID | Title | Primary FR Mapping | Secondary FR Mapping |
| --- | --- | --- | --- |
| EP-DATA-001 | FHIR Batch Intake Foundation | FR-001 | FR-011 |
| EP-DATA-002 | Canonical Resource Normalization | FR-002 | None |
| EP-DATA-003 | Linkage Validation and Completeness Guards | FR-002, FR-005 | FR-011 |
| EP-DATA-004 | Ingestion Traceability and Replay Artifacts | FR-006, FR-012 | None |

## Prioritization

1. EP-DATA-001 is first because no downstream module can run without a controlled batch-ingestion surface.
2. EP-DATA-002 is second because deterministic contradiction rules depend on canonical normalized fields.
3. EP-DATA-003 is third because completeness and linkage states must be distinguished before rule evaluation.
4. EP-DATA-004 is fourth because replay and provenance should be built into the ingestion layer before audit findings are produced at scale.

## Assumptions and Dependencies

- The ingestion layer remains audit-only and must not perform diagnostic interpretation.
- The six in-scope FHIR resource classes in the specification remain stable for the first vertical slice.
- Shared models for normalized resources and ingest provenance must be created before significant ingestion logic is added.
- Benchmark and sample FHIR bundles are still missing from the repository and must be created to validate these epics.
- The code analysis artifact confirms the product codebase is currently scaffold-stage, so these epics represent forward delivery work rather than decomposition of existing implemented features.

## Recommended Next Slice

Start with EP-DATA-001 and EP-DATA-002 together as the first thin vertical slice. That pairing creates the minimum safe path to accept a batch, normalize it into canonical models, and hand deterministic rule evaluation a stable contract.
