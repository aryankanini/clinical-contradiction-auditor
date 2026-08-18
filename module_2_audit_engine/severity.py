"""Deterministic severity scoring for audit findings."""

from __future__ import annotations

from module_2_audit_engine.models.finding import Finding


RULE_WEIGHTS = {
	"RULE-COND-004": 5,
	"RULE-MED-001": 4,
	"RULE-MED-004": 4,
	"RULE-ENC-002": 3,
	"RULE-PROC-002": 3,
	"RULE-OBS-002": 3,
	"RULE-STALE-001": 2,
	"RULE-CARE-003": 1,
}


class SeverityCalculator:
	"""Calculate a repeatable severity tier from finding context."""

	@staticmethod
	def calculate_score(finding: Finding) -> int:
		weight = RULE_WEIGHTS.get(finding.rule_id, 2)
		resource_impact = 2 if len(finding.resource_references) >= 2 else 0
		business_outcome = 3 if finding.category == "medication" else 2 if finding.category == "diagnosis" else 1
		return weight + resource_impact + business_outcome

	@classmethod
	def calculate(cls, finding: Finding) -> str:
		score = cls.calculate_score(finding)
		if score >= 10:
			return "CRITICAL"
		if score >= 7:
			return "HIGH"
		if score >= 4:
			return "MEDIUM"
		return "LOW"
