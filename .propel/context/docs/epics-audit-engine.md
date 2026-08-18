# Audit Engine Epics & User Stories

## Overview

This document defines epics and user stories for **module_2_audit_engine** — the deterministic contradiction detection backbone of the Clinical Data Integrity Auditor. All epics are prefixed `EP-AE-` for clear audit-engine scoping.

**Project Type:** Brown-field (scaffold in place, zero implementation)  
**Foundational Dependency:** module_1_data (normalized FHIR resources)  
**Safety Model:** Deterministic-first with audit-only boundary enforcement  
**Total Audit Engine Scope:** ~49 person-days across 4 epics  

---

## Epic Summary Table

| Epic ID | Epic Title | Estimated Effort | Mapped Requirement IDs | Dependencies |
|---------|-----------|-------------------|------------------------|--------------|
| EP-AE-001 | Rule Engine Framework & Execution | 12 person-days | FR-003, FR-011 | None |
| EP-AE-002 | Cross-Resource Contradiction Detection | 15 person-days | FR-003, FR-004, FR-005 | EP-AE-001 |
| EP-AE-003 | Timeline & State Validation Rules | 10 person-days | FR-004 | EP-AE-001 |
| EP-AE-004 | Severity Scoring & Transparency Emission | 12 person-days | FR-006, FR-008, FR-012 | EP-AE-001 |

---

## Epic Descriptions

### EP-AE-001: Rule Engine Framework & Execution

**Business Value:**  
Establish the deterministic rule execution foundation that is the authoritative source for all contradiction detection. This epic makes it impossible for AI or downstream systems to alter contradiction status post-detection.

**Description:**  
Build the core rule engine framework including rule loading, validation, versioning, execution scheduling, and safety-bound audit-only enforcement. Implement a rule interface that guarantees deterministic outputs and prevents clinical intent mutation. All subsequent contradiction and validation rules will consume this framework.

**UI Impact:** No

**Key Deliverables:**
- Rule interface contract (Python ABC) specifying signature, inputs, outputs, side-effect constraints
- Rule loader that deserializes YAML rule pack with version metadata
- Rule pack validator (syntax, dependency graphs, safety boundary checks)
- Rule execution orchestrator with execution plan + audit-trail logging
- Safety gate that enforces rule outputs are immutable after initial evaluation
- Unit tests covering rule interface contracts, versioning, and safety boundaries
- Integration test with sample rule pack proving deterministic repeatability

**Dependent EPICs:**
- None

**User Stories in This Epic:**
- US-AE-001: Rule Interface Contract & Loader
- US-AE-002: Rule Pack Versioning & Validation
- US-AE-003: Rule Execution Orchestrator
- US-AE-004: Safety Boundary Enforcement & Audit Logging

**Acceptance Criteria (Epic-Level):**
- [ ] Rule execution produces identical outputs from identical inputs (reproducible)
- [ ] Every rule execution is logged with rule ID, version, input resources, outputs, timestamp
- [ ] No rule output can be mutated or bypassed after initial evaluation
- [ ] Rule pack syntax and dependency validation prevent misconfiguration
- [ ] 100% of rules execute or fail cleanly (no silent skips)

---

### EP-AE-002: Cross-Resource Contradiction Detection

**Business Value:**  
Detect contradictions across related FHIR resources (Conditions, Medications, Procedures, Encounters, Observations, CarePlans) — the primary product feature that surfaces invisible consistency issues.

**Description:**  
Implement rule sets that evaluate relationships and state consistency across multiple resource types. Examples include: active medication referenced in inactive care plan, diagnosis with end date but ongoing encounter, medication with incompatible indication and condition, procedure status inconsistent with related encounter timeline. Rules are deterministic, executed in batch against normalized resources, and emit evidence-linked contradiction findings.

**UI Impact:** No

**Screen References:** N/A (backend logic)

**Key Deliverables:**
- Condition rule set (diagnoses, status lifecycle, referenced care plans)
- Medication rule set (active/inactive status, indication, related conditions, care plan linkage)
- Procedure rule set (status, encounter linkage, timeline consistency)
- Encounter rule set (status, related conditions, medications, procedures)
- Observation rule set (status, related conditions, timelines)
- CarePlan rule set (status, referenced conditions, medications, procedures)
- Evidence extractor that links contradicted resources back to rule
- Contradiction finding schema with required transparency fields
- Integration tests with labeled contradiction scenarios

**Dependent EPICs:**
- EP-AE-001 - Foundational - Requires rule execution framework

**User Stories in This Epic:**
- US-AE-005: Condition Cross-Resource Contradiction Rules
- US-AE-006: Medication Cross-Resource Contradiction Rules
- US-AE-007: Encounter, Procedure, Observation, CarePlan Cross-Resource Rules
- US-AE-008: Evidence Extraction & Finding Emission

**Acceptance Criteria (Epic-Level):**
- [ ] At least 8 distinct contradiction patterns are implemented as rules
- [ ] Each contradiction rule identifies ≥2 involved resources
- [ ] Rules are agnostic to resource load order (deterministic)
- [ ] Evidence references point to exact fields and values that contradict
- [ ] Test cases cover at least 20 known contradiction scenarios with labeled truth sets

---

### EP-AE-003: Timeline & State Validation Rules

**Business Value:**  
Detect stale states, impossible event sequences, and temporal consistency violations — critical for identifying data drift and operational integrity issues.

**Description:**  
Implement deterministic timeline and state-lifecycle validation rules. Examples include: medication with end date in the future vs. current date, encounter closed but still referenced by open procedures, diagnosis with impossible resolution timestamp, condition status transitions that violate clinical lifecycle rules. Rules evaluate temporal consistency using normalized timestamp fields and resource state enums.

**UI Impact:** No

**Key Deliverables:**
- Stale state detection rule set (resources with outdated terminal states)
- Temporal ordering validation (events must sequence logically)
- State lifecycle transition rules (valid state paths per resource type)
- Timeline intersection rules (overlapping or conflicting date ranges)
- Integration tests with temporal contradiction scenarios
- Documentation of timeline assumptions (time zone handling, epoch precision)

**Dependent EPICs:**
- EP-AE-001 - Foundational - Requires rule execution framework

**User Stories in This Epic:**
- US-AE-009: Stale State Detection Rules
- US-AE-010: Temporal Ordering & State Lifecycle Validation

**Acceptance Criteria (Epic-Level):**
- [ ] Stale state detection identifies resources with end dates ≥X days in past (X configurable)
- [ ] Impossible event sequences are flagged (e.g., procedure after encounter close)
- [ ] State lifecycle rules prevent invalid transitions per resource type
- [ ] All rules are timezone-aware and handle epoch precision consistently
- [ ] Test coverage includes edge cases: leap years, DST boundaries, null timestamps

---

### EP-AE-004: Severity Scoring & Transparency Emission

**Business Value:**  
Assign risk-based priority to findings and emit complete audit transparency — enabling operators to triage high-impact issues first and satisfy compliance reproducibility requirements.

**Description:**  
Implement finding severity scoring based on rule-defined criteria and resource criticality. Emit every finding with mandatory transparency fields: rule ID, records evaluated, evidence references, timestamp, and audit outcome. Persist findings to immutable audit log for reproducibility and compliance review. Severity tiers drive queue routing and SLA escalation downstream.

**UI Impact:** No

**Key Deliverables:**
- Severity scoring algorithm (rule weight + resource impact + business outcome)
- Severity tier definitions (CRITICAL, HIGH, MEDIUM, LOW)
- Transparency field population (rule ID, resources, evidence, timestamp, audit outcome)
- Audit log schema and persistence
- Finding hydration (combining rule output + severity + evidence into complete packet)
- Reproducibility verification (sampled finding can be reconstructed from log artifacts)
- Integration tests proving 100% of findings include all transparency fields
- Compliance audit trail (who reviewed, when, what action taken)

**Dependent EPICs:**
- EP-AE-001 - Foundational - Requires rule execution framework

**User Stories in This Epic:**
- US-AE-011: Severity Scoring Algorithm & Tier Assignment
- US-AE-012: Transparency Field Emission & Finding Hydration
- US-AE-013: Audit Log Persistence & Reproducibility Validation

**Acceptance Criteria (Epic-Level):**
- [ ] Every finding has rule ID, record IDs, evidence summary, timestamp, audit outcome
- [ ] Severity score is deterministic (same input → same score)
- [ ] ≥90% of findings are populated with all transparency fields (quality gate)
- [ ] Audit log stores sufficient metadata to reproduce findings without re-running pipeline
- [ ] Compliance sampling can reconstruct ≥95% of findings from persisted artifacts

---

## User Stories

### User Story: US-AE-001
**Epic:** EP-AE-001  
**Title:** Rule Interface Contract & Loader  
**Story:** As a deterministic rule engine, I need to load and validate rule definitions from a versioned YAML catalog so that rules can be executed in a predictable, auditable manner.

**Acceptance Criteria:**
- [ ] Rule interface (ABC) defines method signature: `execute(normalized_resources: Dict[str, List]) -> List[Finding]`
- [ ] Rule must include metadata: rule_id, version, description, resource_types_in_scope, safety_boundary_tags
- [ ] Loader deserializes YAML rule pack and instantiates rule objects
- [ ] Loader validates rule_id uniqueness, version format (semver), and mandatory fields
- [ ] Invalid rule pack (missing fields, duplicate IDs) raises ValidationError with clear messages
- [ ] Rule execution is deterministic: same input produces same output every time
- [ ] Unit tests cover: valid pack loading, invalid pack rejection, duplicate ID detection, versioning

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** None

---

### User Story: US-AE-002
**Epic:** EP-AE-001  
**Title:** Rule Pack Versioning & Validation  
**Story:** As a compliance auditor, I need to confirm that the rule version used in a batch audit is known and auditable so that findings can be linked to the exact rule logic that generated them.

**Acceptance Criteria:**
- [ ] Rule pack includes version metadata (major.minor.patch, release date, change log)
- [ ] Active rule version is persisted with batch audit run (rule_pack_version in audit metadata)
- [ ] Rule pack validator checks: syntax, rule dependency graphs (no circular deps), safety tag presence
- [ ] Validation rejects rules that modify resource state or emit diagnostic/clinical claims
- [ ] Rule version history is retrievable (e.g., "show me all findings that used rule pack v2.1.0")
- [ ] Integration test: load v2.0, audit batch X, then load v2.1, replay same batch, compare outputs (outputs differ if rules changed, same if logic unchanged)
- [ ] Safety gate: old rule pack versions are immutable after release (read-only archive)

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** US-AE-001

---

### User Story: US-AE-003
**Epic:** EP-AE-001  
**Title:** Rule Execution Orchestrator  
**Story:** As a batch audit runner, I need to orchestrate deterministic rule evaluation across all patient resources in a cohort so that findings can be systematically logged and reproducible.

**Acceptance Criteria:**
- [ ] Orchestrator loads active rule pack, normalizes patient resources, executes all rules
- [ ] Execution plan is built upfront (list of rules to run, order, estimated runtime)
- [ ] Each rule execution captures: rule_id, version, input resource snapshot, output findings, timestamp, execution duration
- [ ] Rule execution is transaction-like: either produces findings or fails cleanly (no partial states)
- [ ] If a rule raises an exception, batch audit logs the failure, records which rule failed, and continues with remaining rules
- [ ] Findings are emitted in deterministic order (sorted by rule ID, then resource ID)
- [ ] No rule output is cached or reused across batch runs (fresh execution every time)
- [ ] Integration test: execute same batch 3 times, confirm output order and content are identical

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** US-AE-001, US-AE-002

---

### User Story: US-AE-004
**Epic:** EP-AE-001  
**Title:** Safety Boundary Enforcement & Audit Logging  
**Story:** As a compliance enforcer, I need every rule execution to be logged and rule outputs to be immutable so that the audit-only boundary is provably maintained.

**Acceptance Criteria:**
- [ ] All rule executions (entry, input, output, errors, duration) are logged to audit trail
- [ ] Log entries include: timestamp (ISO 8601), rule_id, batch_run_id, rule version, input snapshot hash, output finding count
- [ ] Finding outputs are immutable after rule execution (sealed in audit log)
- [ ] Audit log is append-only (cannot delete or modify past entries)
- [ ] Log schema includes: execution_id (UUID), rule_id, version, cohort_size, findings_emitted, errors, duration_ms, executor_identity
- [ ] Safety gate: every finding emission includes check that rule output is deterministic (no randomness, no timestamp variation)
- [ ] Unit test: verify that finding object cannot be mutated after sealing
- [ ] Integration test: audit log reproduces exact execution flow including errors and skips

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** US-AE-001, US-AE-003

---

### User Story: US-AE-005
**Epic:** EP-AE-002  
**Title:** Condition Cross-Resource Contradiction Rules  
**Story:** As a data quality reviewer, I need to detect contradictions involving Condition resources (e.g., active condition but care plan closed) so that diagnosis consistency issues are surfaced before clinical use.

**Acceptance Criteria:**
- [ ] Rule 1: Condition is active but all related CarePlans are closed (contradiction: active care needed but plan inactive)
- [ ] Rule 2: Condition has end date in past but referenced as active in current Encounter
- [ ] Rule 3: Condition status is terminal (resolved/entered-in-error) but linked to ongoing Encounter or open Procedure
- [ ] Rule 4: Condition references a Medication that is inactive or has end date before condition start
- [ ] Each rule identifies involved resources: Condition ID, related resource IDs, conflicting fields
- [ ] Evidence payload includes: field names, actual values, expected state, rule logic summary
- [ ] Rules execute in <100ms per patient record (performance SLA)
- [ ] Test cases: ≥5 labeled contradiction scenarios per rule with expected findings

**Effort Estimate:** L (10 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001

---

### User Story: US-AE-006
**Epic:** EP-AE-002  
**Title:** Medication Cross-Resource Contradiction Rules  
**Story:** As a medication safety auditor, I need to detect contradictions involving Medication resources (e.g., medication status conflicts, indication mismatches) so that medication consistency issues do not propagate to care teams.

**Acceptance Criteria:**
- [ ] Rule 1: Medication marked active but no active or ongoing CarePlan references it
- [ ] Rule 2: Medication status is completed/stopped but Encounter or Condition references it as active
- [ ] Rule 3: Medication indication (code) is inconsistent with stated Condition (e.g., antibiotic for non-infection)
- [ ] Rule 4: Medication has end date but is referenced in a future-dated Encounter or ongoing CarePlan
- [ ] Rule 5: Medication dosage status conflicts with higher-level medication resource status
- [ ] Each rule identifies involved resources: Medication ID, Condition/Encounter/CarePlan IDs, conflicting fields
- [ ] Evidence includes: field names, actual values, related resource states, rule logic
- [ ] Rules execute in <100ms per patient record
- [ ] Test cases: ≥5 labeled contradiction scenarios per rule

**Effort Estimate:** L (10 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001

---

### User Story: US-AE-007
**Epic:** EP-AE-002  
**Title:** Encounter, Procedure, Observation, CarePlan Cross-Resource Rules  
**Story:** As a clinical audit lead, I need to detect contradictions across Encounters, Procedures, Observations, and CarePlans so that the full patient record consistency is assured.

**Acceptance Criteria:**
- [ ] **Encounter Rules:**
  - Encounter status is complete but linked Procedures are still in-progress
  - Encounter end date is before start date
  - Referenced Conditions have onset after encounter end
- [ ] **Procedure Rules:**
  - Procedure status is completed but referenced Encounter is not completed
  - Procedure date is outside Encounter date range
  - Procedure status transitions violate clinical sequence (e.g., not-done after completed)
- [ ] **Observation Rules:**
  - Observation date is outside related Encounter date range
  - Observation references Condition with status terminal
  - Observation result contradicts related Condition status
- [ ] **CarePlan Rules:**
  - CarePlan status is active but has no referenced Conditions
  - CarePlan is completed but contains active Medications or Procedures
  - CarePlan period is inconsistent with status
- [ ] Cross-linking: contradictions span ≥2 resource types, evidence identifies all involved resources
- [ ] Test cases: ≥3 scenarios per rule type with labeled truth sets

**Effort Estimate:** L (10 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001

---

### User Story: US-AE-008
**Epic:** EP-AE-002  
**Title:** Evidence Extraction & Finding Emission  
**Story:** As a finding reviewer, I need each contradiction finding to include direct links to the contradicted resources and the exact fields that conflict so that I can investigate without secondary queries.

**Acceptance Criteria:**
- [ ] Finding object includes: rule_id, rule_version, resource_ids (all involved), contradiction_type, evidence_summary, conflicting_field_names, field_values
- [ ] Evidence summary is human-readable (e.g., "Medication (ID: med-123) status='active' but CarePlan (ID: cp-456) status='completed' and end_date='2024-08-01'")
- [ ] Finding includes FHIR resource references (not full resources; reference form: {resource_type}/{id})
- [ ] Contradicted fields are indexed (e.g., ["status", "end_date"]) so queries can group findings by field type
- [ ] Finding JSON schema validates against canonical schema (SchemaVer 1.0)
- [ ] ≥95% of findings populate all evidence fields (quality gate)
- [ ] Test: 50 sample findings from different rules produce parseable, complete evidence payloads

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** US-AE-005, US-AE-006, US-AE-007

---

### User Story: US-AE-009
**Epic:** EP-AE-003  
**Title:** Stale State Detection Rules  
**Story:** As a data governance steward, I need to detect resources in terminal states that are outdated (not updated in X days) so that stale records don't masquerade as current.

**Acceptance Criteria:**
- [ ] Stale state rule evaluates: resource status is terminal (resolved, completed, entered-in-error) AND last_update_date is >90 days ago (configurable threshold)
- [ ] Applies to: Condition, Medication, Procedure, Encounter, CarePlan, Observation (all resource types)
- [ ] Generates finding with: resource_id, resource_type, status, last_update_date, staleness_days, rule_threshold
- [ ] Excludes resources with explicitly documented archival intent (e.g., archive_date field)
- [ ] Rule threshold is configurable per resource type (e.g., Medication stale after 30 days, Condition after 90)
- [ ] Evidence includes: current date, last update date, days stale, reason stale matters (e.g., "affects future care decisions")
- [ ] Test cases: resources at threshold boundary, just-expired resources, explicitly archived resources

**Effort Estimate:** M (5 person-days)  
**Priority:** SHOULD  
**Dependencies:** EP-AE-001

---

### User Story: US-AE-010
**Epic:** EP-AE-003  
**Title:** Temporal Ordering & State Lifecycle Validation  
**Story:** As a timeline auditor, I need to detect impossible event sequences and invalid state transitions so that temporal data integrity is assured.

**Acceptance Criteria:**
- [ ] **Temporal Ordering Rule:** Linked resources must have consistent date ordering (e.g., Condition onset ≤ Encounter start ≤ Procedure date)
- [ ] **State Lifecycle Rule:** Resource state transitions must follow valid paths (e.g., active → on-hold → completed, but NOT active → resolved → active)
- [ ] State paths are defined per resource type (static configuration)
- [ ] Finds contradictions: event dates inverted (end before start), impossible sequences (condition resolved before onset), future-dated terminal states
- [ ] Handles null/missing dates gracefully (logs as data quality issue, not contradiction)
- [ ] Timezone-aware: timestamps normalized to UTC before comparison
- [ ] Evidence includes: actual event dates, expected sequence, which transition is invalid
- [ ] Test cases: leap years, DST boundaries, null timestamps, epoch precision edge cases

**Effort Estimate:** M (5 person-days)  
**Priority:** SHOULD  
**Dependencies:** EP-AE-001

---

### User Story: US-AE-011
**Epic:** EP-AE-004  
**Title:** Severity Scoring Algorithm & Tier Assignment  
**Story:** As a triage coordinator, I need findings automatically assigned a severity tier (CRITICAL, HIGH, MEDIUM, LOW) based on risk so that operations can prioritize high-impact issues.

**Acceptance Criteria:**
- [ ] Severity algorithm factors: rule weight (rule-defined, e.g., 1–5), resource impact (how many resources affected), business outcome (does it block care or affect compliance)
- [ ] **CRITICAL:** multi-resource contradictions affecting active medications or active care plans, or findings that violate regulatory requirements
- [ ] **HIGH:** contradictions affecting historical conditions or archived resources, or 3+ resources involved
- [ ] **MEDIUM:** single-resource state issues (stale states), non-blocking temporal violations
- [ ] **LOW:** deprecated resources, documentation-only fields, informational inconsistencies
- [ ] Severity is deterministic: same rule + resources → same tier every run
- [ ] Algorithm is documented (decision tree or scoring formula)
- [ ] At least 80% of findings receive a severity tier (no unscored findings)
- [ ] Test: 30 diverse findings score consistently across multiple runs

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001, US-AE-005 through US-AE-010

---

### User Story: US-AE-012
**Epic:** EP-AE-004  
**Title:** Transparency Field Emission & Finding Hydration  
**Story:** As a compliance auditor, I need every finding to include mandatory transparency fields so that findings are reproducible and auditable.

**Acceptance Criteria:**
- [ ] Mandatory transparency fields: rule_id, rule_version, batch_run_id, timestamp (ISO 8601), audit_outcome (finding confirmed/rejected), resources_evaluated (IDs), evidence_payload, severity_tier
- [ ] Finding is fully hydrated before emission: no null mandatory fields
- [ ] Hydration pipeline: rule output → extract evidence → assign severity → stamp timestamp → emit
- [ ] ≥90% of findings populate all transparency fields (quality gate; failures routed to data remediation queue)
- [ ] Transparency fields are immutable after emission (sealed in persistence layer)
- [ ] Evidence payload is complete: contradicted field names, actual values, conflicting resource states
- [ ] Timestamp resolution: millisecond (sufficient for reproducibility)
- [ ] Test: generate 100 diverse findings, verify all have all transparency fields

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001, US-AE-008

---

### User Story: US-AE-013
**Epic:** EP-AE-004  
**Title:** Audit Log Persistence & Reproducibility Validation  
**Story:** As a compliance officer, I need to verify that sampled findings can be reproduced from persisted audit logs so that findings are defensible in audit and legal review.

**Acceptance Criteria:**
- [ ] Audit log stores per-batch: batch_run_id, rule_pack_version, cohort_size, timestamp_start, timestamp_end, findings_emitted, errors_occurred
- [ ] Per-finding log: rule_id, rule_version, input_resource_snapshot_hash, output_finding_hash, evidence_payload, timestamp, executor_identity
- [ ] Reproducibility validation: given a batch_run_id + rule_pack_version, system can replay findings from log without re-running rules
- [ ] Persistence is append-only and immutable (use immutable schema or read-only archive after N days)
- [ ] Audit log is queryable by: batch_run_id, rule_id, severity_tier, resource_id, date range
- [ ] ≥95% of findings are reproducible from log artifacts (test on sample)
- [ ] Log retention policy: ≥7 years for compliance (configurable)
- [ ] Integration test: select 10 random findings, reconstruct from log, confirm match to original

**Effort Estimate:** M (5 person-days)  
**Priority:** MUST  
**Dependencies:** EP-AE-001, US-AE-012

---

## Dependency & Sequencing Summary

```
EP-AE-001 (Rule Engine Foundation) — FOUNDATIONAL
  ↓
  ├── EP-AE-002 (Cross-Resource Contradictions) [parallel start OK after EP-AE-001 done]
  ├── EP-AE-003 (Timeline & State Validation)   [parallel start OK after EP-AE-001 done]
  └── EP-AE-004 (Severity & Transparency)       [parallel start OK after EP-AE-001 done]
```

**Critical Path:** EP-AE-001 (12 days) → any of {EP-AE-002, EP-AE-003, EP-AE-004} (can run in parallel, ~15 days critical path with EP-AE-002 as largest)

**Total Duration:** ~27 days (12 + 15 parallel)  
**Team Capacity:** 2–3 developers recommended (one owns EP-AE-001, others tackle EP-AE-002/003/004 in parallel)

---

## Quality Gates

- [ ] All 12 user stories have acceptance criteria that are testable and deterministic
- [ ] All functional requirements (FR-003, FR-004, FR-005, FR-006, FR-008, FR-011, FR-012) are mapped to at least one US
- [ ] Each epic's estimated person-days ≤60 (all epics are 10–15 days; total 49 days)
- [ ] No cross-feature dependencies (audit engine is self-contained; external dependencies on module_1_data are implicit)
- [ ] Safety boundary is enforced in US-AE-004 and US-AE-012
- [ ] Transparency fields are mandatory in US-AE-012, US-AE-013, and US-AE-008
- [ ] Reproducibility is validated in US-AE-013
- [ ] ≥90% of findings populate all transparency fields (success criterion)

---

## Output Artifacts

1. **epics-audit-engine.md** (this document) — Epic summaries, user stories, dependencies, quality gates
2. **user-story files** (to be generated):
   - `.propel/tasks/EP-AE-001/us_001/us_001.md` (Rule Interface Contract & Loader)
   - `.propel/tasks/EP-AE-001/us_002/us_002.md` (Rule Pack Versioning & Validation)
   - `.propel/tasks/EP-AE-001/us_003/us_003.md` (Rule Execution Orchestrator)
   - `.propel/tasks/EP-AE-001/us_004/us_004.md` (Safety Boundary Enforcement)
   - `.propel/tasks/EP-AE-002/us_005/us_005.md` (Condition Contradiction Rules)
   - `.propel/tasks/EP-AE-002/us_006/us_006.md` (Medication Contradiction Rules)
   - `.propel/tasks/EP-AE-002/us_007/us_007.md` (Encounter/Procedure/Observation/CarePlan Rules)
   - `.propel/tasks/EP-AE-002/us_008/us_008.md` (Evidence Extraction & Finding Emission)
   - `.propel/tasks/EP-AE-003/us_009/us_009.md` (Stale State Detection)
   - `.propel/tasks/EP-AE-003/us_010/us_010.md` (Temporal Ordering & State Lifecycle)
   - `.propel/tasks/EP-AE-004/us_011/us_011.md` (Severity Scoring Algorithm)
   - `.propel/tasks/EP-AE-004/us_012/us_012.md` (Transparency Field Emission)
   - `.propel/tasks/EP-AE-004/us_013/us_013.md` (Audit Log Persistence & Reproducibility)

---

## Validation Checklist

- [x] All requirements from spec § Functional Requirements (FR-003 through FR-012) mapped
- [x] All requirements from spec § Use Cases (UC-001 audit, UC-002 triage relevant) mapped
- [x] BRD problem statements (cross-resource contradictions, stale states, missing relationships) all addressed
- [x] Codeanalysis gaps (no rule catalog, no shared data model) partially addressed (rule catalog is artifact deliverable; data model assumed from module_1_data)
- [x] Safety boundary (FR-011, audit-only, no diagnosis) enforced in EP-AE-001 and EP-AE-004
- [x] Reproducibility (FR-012) enforced in EP-AE-004
- [x] Transparency (FR-006) enforced in EP-AE-004
- [x] No orphaned requirements
- [x] No circular dependencies
- [x] Each epic ≤60 person-days
- [x] Total audit engine scope ~49 person-days (well-scoped)
