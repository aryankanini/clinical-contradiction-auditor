from module_2_audit_engine.evidence_extractor import extract_evidence
from module_2_audit_engine.finding_hydrator import FindingHydrator
from module_2_audit_engine.reproducibility import ReproducibilityValidator
from module_2_audit_engine.rules.diagnosis_rules import RuleCondition001


def test_scored_hydrated_finding_is_reproducible() -> None:
	resources = [{"resourceType": "Condition", "id": "condition-1", "clinicalStatus": {"text": "active"}, "onsetDateTime": "2026-08-18T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}}]
	raw = RuleCondition001().execute(resources)[0]
	archived = FindingHydrator.hydrate(extract_evidence(raw, resources, "batch-1", "2026-08-17T00:00:00Z"), "Active condition onset exceeds the audit reference date.")
	replayed = FindingHydrator.hydrate(extract_evidence(raw, resources, "batch-1", "2026-08-17T00:00:00Z"), "Active condition onset exceeds the audit reference date.")

	report = ReproducibilityValidator.validate([archived], [replayed])
	assert archived.severity_tier == "MEDIUM"
	assert archived.evidence_completeness_pct == 100.0
	assert report.passed