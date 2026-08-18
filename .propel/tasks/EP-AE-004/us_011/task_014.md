---
taskId: task_014
epicId: EP-AE-004
parentStories: [us_011, us_012]
title: "Implement Severity Scoring & Transparency Field Hydration"
priority: P1-High
status: PLANNED
estimatedHours: 8
---

# Task: Implement Severity Scoring & Transparency Field Hydration

## Objective

Implement deterministic severity scoring algorithm and complete transparency field hydration. Assign CRITICAL/HIGH/MEDIUM/LOW tiers to findings based on rule weight, resource impact, and business outcome.

---

## Acceptance Criteria Mapping

- **us_011 AC-1:** Severity scoring algorithm implemented (CRITICAL ≥10, HIGH 7-9, MEDIUM 4-6, LOW <4)
- **us_012 AC-1:** All transparency fields populated (≥80% findings)
- **us_012 AC-2:** Transparency fields enable reproducibility

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `module_2_audit_engine/severity.py` | CREATE/MODIFY | Severity scoring algorithm, tier assignment |
| `module_2_audit_engine/finding_hydrator.py` | CREATE | Transparency field assembly and hydration |

---

## Severity Scoring Algorithm

**Formula:**
```
severity_score = rule_weight + resource_impact + business_outcome

Where:
  rule_weight ∈ [1, 5]      (e.g., 5 = critical rule, 1 = informational)
  resource_impact ∈ [0, 2]   (e.g., 2 = multiple resources affected, 0 = single resource)
  business_outcome ∈ [0, 3]  (e.g., 3 = patient safety impact, 0 = data quality only)

Tier Mapping:
  score ≥ 10  → CRITICAL  (e.g., 5 + 2 + 3 = 10)
  score 7-9   → HIGH      (e.g., 4 + 2 + 3 = 9)
  score 4-6   → MEDIUM    (e.g., 3 + 2 + 1 = 6)
  score < 4   → LOW       (e.g., 1 + 0 + 0 = 1)
```

**Rule Weight Mapping:**
| Rule ID | Category | Weight | Rationale |
|---------|----------|--------|-----------|
| RULE-COND-004 | Condition entered-in-error | 5 | Data integrity critical |
| RULE-MED-001/004 | Medication status/dose | 4 | Patient safety risk |
| RULE-ENC-002/PROC-002/OBS-002 | Timeline violations | 3 | Audit trail importance |
| RULE-STALE-001 | Stale state | 2 | Data relevance concern |
| RULE-CARE-003 | CarePlan no activities | 1 | Informational |

---

## Transparency Field Hydration

**Fields to Hydrate (from Finding model in task_008):**
- rule_id, rule_version (from rule execution)
- batch_run_id, timestamp_utc (from execution context)
- audit_outcome (derived from finding type)
- severity_tier (calculated by severity algorithm)
- resources_evaluated, resource_count (extracted from input)
- evidence_payload, evidence_completeness_pct (from evidence extractor)
- rule_logic_summary (from rule metadata/docstring)
- finding_narrative (generated from evidence)
- input_snapshot_hash, output_finding_hash (from hashing)

**Completeness Target:** ≥80% findings have all transparency fields populated

---

## Implementation Checklist

- [ ] Define severity scoring algorithm (rule_weight + resource_impact + business_outcome)
- [ ] Create score → tier mapping (CRITICAL ≥10, HIGH 7-9, MEDIUM 4-6, LOW <4)
- [ ] Define rule_weight for all 18 rules (captured in rule metadata YAML)
- [ ] Implement SeverityCalculator class (static method: calculate(finding) → severity_tier)
- [ ] Implement FindingHydrator class (populate all transparency fields)
- [ ] Add rule_logic_summary extraction (from rule docstring or metadata)
- [ ] Generate finding_narrative (natural language from evidence)
- [ ] Calculate evidence_completeness_pct (count non-null fields / total fields)
- [ ] Write unit tests (≥5 scenarios: score calculation, tier mapping, hydration)
- [ ] Verify determinism (same input → same score always)

---

## Technical Notes

- Severity scoring: deterministic (same rule + resources → same score)
- Rule weight: configured in YAML rule pack or rule metadata
- Resource impact: heuristic (1 resource = 0, 2+ resources = 2)
- Business outcome: inferred from rule category (medication = 3, etc.)
- Finding narrative generation: template-based (e.g., "Condition marked active but onset is 21 months in future")
- Transparency completeness: measure empirically; report findings below 80%

---

## Edge Cases & Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Rule_weight not specified | Use default weight=2 (medium); log WARN |
| Evidence_payload empty | completeness_pct = 0; still emit finding |
| Rule_logic_summary too long | Truncate to 500 chars; log WARN |
| Finding_narrative generation fails | Use generic narrative template; log ERROR |
| Score calculation overflows | Use integer (Python handles unlimited precision) |

---

## Definition of Done

- [ ] Severity algorithm implemented and deterministic
- [ ] All 18 rules have weight assignments
- [ ] Tier mapping correct (CRITICAL ≥10, HIGH 7-9, MEDIUM 4-6, LOW <4)
- [ ] Hydrator populates all transparency fields
- [ ] Transparency completeness ≥80%
- [ ] Rule narrative generation working
- [ ] Evidence completeness calculated
- [ ] Unit tests pass (≥5 scenarios)
- [ ] No linting issues
- [ ] Code review approved

---

## Dependencies

- **Blocking:** task_008 (Finding model), task_007 (18 rules with weights)
- **Blocked By:** None
- **Related:** task_016 (Testing)

---

**Effort:** 8 hours  
**Owner:** Backend Engineer  
**Review Checklist:** Scoring deterministic, tier mapping correct, hydrator complete, transparency ≥80%, tests pass
