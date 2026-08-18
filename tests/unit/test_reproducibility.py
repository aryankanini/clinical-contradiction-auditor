from module_2_audit_engine.models.finding import Finding
from module_2_audit_engine.reproducibility import ReproducibilityValidator


def finding(finding_id: str, output_hash: str) -> Finding:
	return Finding(rule_id="RULE-001", severity="warning", category="test", finding_id=finding_id, output_finding_hash=output_hash)


def test_reproducibility_validator_accepts_matching_replay() -> None:
	report = ReproducibilityValidator.validate([finding("1", "a"), finding("2", "b")], [finding("1", "a"), finding("2", "b")])
	assert report.validated_count == 2
	assert report.validation_rate == 1.0
	assert report.passed


def test_reproducibility_validator_reports_divergence() -> None:
	report = ReproducibilityValidator.validate([finding("1", "a")], [finding("1", "different")])
	assert report.unvalidated_count == 1
	assert not report.passed