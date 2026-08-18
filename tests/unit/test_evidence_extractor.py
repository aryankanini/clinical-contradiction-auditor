from module_2_audit_engine.evidence_extractor import extract_evidence


def test_extract_evidence_hydrates_deterministic_finding() -> None:
	raw = {"rule_id": "RULE-COND-001", "severity": "warning", "category": "diagnosis", "narrative": "Condition fields conflict.", "evidence": [{"field": "status", "value": "active"}]}
	resources = [{"resourceType": "Condition", "id": "condition-1", "clinicalStatus": {"text": "active"}}]

	first = extract_evidence(raw, resources, "batch-1", "2026-08-17T00:00:00Z")
	second = extract_evidence(raw, resources, "batch-1", "2026-08-17T00:00:00Z")

	assert first == second
	assert first.resource_references == ("Condition/condition-1",)
	assert first.conflicting_fields == ("status",)
	assert first.evidence_completeness_pct == 100.0
	assert len(first.input_snapshot_hash) == len(first.output_finding_hash) == 64