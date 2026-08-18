---
taskId: task_008
epicId: EP-AE-002
parentStories: [us_008]
title: "Evidence Extraction & Finding Schema"
priority: P1-High
status: PLANNED
estimatedHours: 6
---

# Task: Evidence Extraction & Finding Schema

## Objective

Design and implement finding schema with complete evidence hydration. Findings emit all transparency fields (rule_id, version, batch_run_id, timestamp, audit_outcome, evidence_payload) to enable reproducibility and audit trails.

---

## Acceptance Criteria Mapping

- **us_008 AC-1:** Finding schema defined with all transparency fields
- **us_008 AC-2:** Evidence extracted from rules (field names, values, conflicts)
- **us_008 AC-3:** Evidence payload ≥90% field completeness
- **us_008 AC-5:** Findings persisted to database (via task_010)

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/models/finding.py` | CREATE | Finding model, evidence schema, immutable design |
| `module_2_audit_engine/evidence_extractor.py` | CREATE | Evidence extraction logic, field mapping |
| `tests/unit/test_evidence_extractor.py` | CREATE | Evidence extraction tests |

---

## Finding Schema

```python
@dataclass(frozen=True)
class Finding:
    finding_id: str  # UUID
    rule_id: str
    rule_version: str
    batch_run_id: str
    timestamp_utc: datetime
    audit_outcome: str  # e.g., "CONTRADICTED", "FLAGGED"
    severity_tier: str  # CRITICAL, HIGH, MEDIUM, LOW (populated in task_011)
    
    # Resource Context
    patient_id: str
    resources_evaluated: List[str]  # ["Condition/c1", "Medication/m1"]
    resource_count: int
    
    # Evidence
    evidence_payload: Dict[str, Any]  # {field_name, actual_value, expected_value, conflict_desc}
    evidence_fields_count: int
    evidence_completeness_pct: float  # ≥90% target
    
    # Transparency & Audit
    rule_logic_summary: str  # Human-readable rule description
    finding_narrative: str  # Text summary of finding
    input_snapshot_hash: str  # SHA256 of input resources
    output_finding_hash: str  # SHA256 of this finding
    
    # Status
    status: str  # EMITTED, VALIDATED, SUPERSEDED
    created_at: datetime
    
    # Reproducibility
    finding_reproducible: bool = False  # Set in task_015 validation
    reproducibility_notes: Optional[str] = None
```

---

## Evidence Payload Structure

```python
evidence_payload = {
    "contradiction_type": "status_onset_conflict",
    "fields_involved": ["status", "onsetDateTime"],
    "violations": [
        {
            "field": "status",
            "actual_value": "active",
            "expected_value": "cancelled",  # or N/A if no expectation
            "reason": "Active status with future onset date"
        },
        {
            "field": "onsetDateTime",
            "actual_value": "2025-12-31T00:00:00Z",
            "expected_value": "2023-01-01 to 2024-12-31",
            "reason": "Onset date is in the future"
        }
    ],
    "affected_resources": [
        {
            "resource_type": "Condition",
            "resource_id": "Condition/cond-001",
            "conflicting_fields": ["status", "onsetDateTime"]
        }
    ],
    "additional_context": {
        "current_date": "2024-03-15T00:00:00Z",
        "severity_indicator": "Condition marked active but onset is 21 months in future"
    }
}
```

---

## Implementation Checklist

- [ ] Define Finding dataclass (immutable, frozen=True)
- [ ] Define EvidencePayload structure (nested dicts, lists)
- [ ] Implement evidence_extractor.py with extract_evidence(rule_result) → evidence_payload
- [ ] Map rule output → Finding model (populate all transparency fields)
- [ ] Calculate evidence_completeness_pct (count non-null evidence fields / total fields)
- [ ] Generate input_snapshot_hash (SHA256 of input resources JSON)
- [ ] Generate output_finding_hash (SHA256 of Finding model JSON)
- [ ] Implement finding_id generation (UUID, immutable)
- [ ] Add finding factory for consistent creation across all rules
- [ ] Write extraction tests (≥3 scenarios: full evidence, partial evidence, missing fields)
- [ ] Document evidence structure in docstrings

---

## Technical Notes

- Finding immutability: frozen dataclass prevents post-creation modification
- Evidence completeness: count non-null fields in evidence_payload; target ≥90%
- Hashing: SHA256 of JSON-serialized objects (deterministic serialization order)
- Finding ID: UUID4 (immutable, unique per finding)
- Timestamp: UTC only, from batch orchestrator (not current time)
- Evidence extraction: called by rules post-execute(), before safety validation
- Extensibility: evidence_payload is untyped Dict[str, Any] to support future rule types

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Rule returns null evidence | Log WARN; create Finding with evidence_payload={}; completeness_pct=0 |
| Evidence field is very large | Truncate to 10KB; log WARN; include truncation note in narrative |
| Circular reference in evidence | Serialize with depth limit (max 3 levels); log if truncated |
| SHA256 computation fails | Log ERROR; set hash to "ERROR"; continue (don't block finding) |
| Finding ID collision | Generate new UUID if conflict detected in registry |

---

## Definition of Done

- [ ] Finding model fully defined (all transparency fields)
- [ ] Evidence extractor implemented (complete field mapping)
- [ ] Evidence completeness calculation working (≥90% target)
- [ ] Input/output hashing functional (deterministic, reproducible)
- [ ] Finding factory creates consistent Finding objects
- [ ] Unit tests pass (extraction, hashing, completeness)
- [ ] No linting issues
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_001-004 (Rule infrastructure), task_007 (Rules producing findings)
- **Blocked By:** None
- **Related:** task_010 (Database persistence), task_014 (Severity scoring extends Finding)

---

## Validation Strategy

- Unit tests: Evidence extraction, completeness calculation, hashing
- Manual review: Finding schema completeness, evidence_payload examples
- Integration: End-to-end flow (rule → evidence → finding → persistence)

---

## Testing Requirements

### Unit Tests (6+ tests)
- test_finding_creation() — Create Finding, verify all fields set
- test_evidence_extraction_full() — Extract evidence, completeness ≥90%
- test_evidence_extraction_partial() — Partial evidence, completeness <90%
- test_input_snapshot_hash() — Compute SHA256, verify deterministic
- test_output_finding_hash() — Compute SHA256 of Finding, verify immutable
- test_finding_immutability() — Attempt modification, verify frozen

### Integration Tests (handled by task_009)
- End-to-end: rule output → evidence extraction → finding emission

---

## External Resources

- Python dataclasses: https://docs.python.org/3.10/library/dataclasses.html#frozen-instances
- SHA256 hashing: https://docs.python.org/3.10/library/hashlib.html
- JSON serialization: https://docs.python.org/3.10/library/json.html

---

**Effort:** 6 hours  
**Sequencing:** Second backend task in EP-AE-002 (after task_007)  
**Owner:** Backend Engineer  
**Review Checklist:** Schema complete, extraction working, completeness calculated, hashing deterministic, tests pass
