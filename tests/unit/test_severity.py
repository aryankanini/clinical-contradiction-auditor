from module_2_audit_engine.finding_hydrator import FindingHydrator
from module_2_audit_engine.models.finding import Finding
from module_2_audit_engine.severity import SeverityCalculator


def make_finding(rule_id: str, category: str = "diagnosis", references: tuple[str, ...] = ()) -> Finding:
	return Finding(rule_id=rule_id, severity="warning", category=category, resource_references=references)


def test_severity_tier_thresholds() -> None:
	assert SeverityCalculator.calculate(make_finding("RULE-COND-004", references=("Condition/1", "Condition/2"))) == "HIGH"
	assert SeverityCalculator.calculate(make_finding("RULE-MED-001", "medication", ("Medication/1", "CarePlan/1"))) == "HIGH"
	assert SeverityCalculator.calculate(make_finding("RULE-CARE-003", "careplan")) == "LOW"


def test_hydrator_returns_immutable_enriched_copy() -> None:
	finding = make_finding("RULE-COND-004", references=("Condition/1", "Condition/2"))
	hydrated = FindingHydrator.hydrate(finding, "x" * 600)

	assert finding.severity_tier == "LOW"
	assert hydrated.severity_tier == "HIGH"
	assert len(hydrated.rule_logic_summary) == 500