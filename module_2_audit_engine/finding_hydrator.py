"""Hydrate immutable findings with deterministic transparency fields."""

from __future__ import annotations

from dataclasses import replace

from module_2_audit_engine.models.finding import Finding
from module_2_audit_engine.severity import SeverityCalculator


class FindingHydrator:
	"""Return a hydrated copy of a finding without changing its source object."""

	@staticmethod
	def hydrate(finding: Finding, rule_logic_summary: str) -> Finding:
		return replace(
			finding,
			severity_tier=SeverityCalculator.calculate(finding),
			rule_logic_summary=rule_logic_summary[:500],
			narrative=finding.narrative or "Audit finding emitted from contradictory resource fields.",
		)