from __future__ import annotations

from time import perf_counter
from typing import Any, Mapping

from module_2_audit_engine.evidence_extractor import extract_evidence
from tests.unit.test_contradiction_rules import RULE_CLASSES


def _contradictory_resources(patient_id: str) -> list[Mapping[str, Any]]:
	return [
		{"resourceType": "Condition", "id": f"condition-{patient_id}", "clinicalStatus": {"text": "active"}, "onsetDateTime": "2026-08-18T00:00:00Z", "abatementDateTime": "2026-08-16T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "MedicationStatement", "id": f"medication-{patient_id}", "status": "active", "effectivePeriod": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}, "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "Observation", "id": f"observation-{patient_id}", "status": "final", "effectiveDateTime": "2026-08-18T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
	]


def test_pipeline_hydrates_rule_findings_with_complete_evidence() -> None:
	resources = _contradictory_resources("1")
	raw_findings = [finding for rule_class in RULE_CLASSES for finding in rule_class().execute(resources)]
	hydrated = [extract_evidence(finding, resources, "batch-pipeline-1", "2026-08-17T00:00:00Z") for finding in raw_findings]

	assert hydrated
	assert all(finding.evidence_completeness_pct == 100.0 for finding in hydrated)
	assert all(finding.resource_references for finding in hydrated)
	assert all(len(finding.input_snapshot_hash) == 64 for finding in hydrated)


def test_rules_complete_thousand_patient_cohort_within_budget() -> None:
	resources = [resource for patient_number in range(1000) for resource in _contradictory_resources(str(patient_number))]

	start = perf_counter()
	findings = [finding for rule_class in RULE_CLASSES for finding in rule_class().execute(resources)]
	elapsed_ms = (perf_counter() - start) * 1000

	assert findings
	assert elapsed_ms < 1000, f"18 rules took {elapsed_ms:.2f}ms for 1,000 patients"