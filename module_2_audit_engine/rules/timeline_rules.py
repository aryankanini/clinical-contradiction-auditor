from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Mapping

from module_2_audit_engine.deterministic.rule_interface import RuleInterface, RuleMetadata
from module_2_audit_engine.rules._rule_utils import finding, iso_datetime, reference_date, resource_id, status


GOVERNED_RELATIONSHIP_RULES: Dict[str, List[str]] = {
	"Condition": ["encounter"],
	"MedicationRequest": ["subject"],
	"Procedure": ["subject"],
	"Encounter": [],
	"Observation": [],
	"CarePlan": ["subject"],
}


def expected_relationships_for(resource_type: str) -> List[str]:
	return GOVERNED_RELATIONSHIP_RULES.get(resource_type, [])


class _TimelineRule(RuleInterface):
	_rule_id = ""
	_name = ""
	_description = ""

	def __init__(self) -> None:
		self._metadata = RuleMetadata(self._rule_id, "1.0.0", self._name, self._description, "timeline")

	@property
	def metadata(self) -> RuleMetadata:
		return self._metadata


class RuleStale001(_TimelineRule):
	"""Find active resources older than the configurable threshold."""

	_rule_id = "RULE-STALE-001"
	_name = "Stale Active State"
	_description = "Finds active resources whose last update predates the stale threshold."

	def __init__(self, threshold_years: int = 5) -> None:
		if threshold_years <= 0:
			raise ValueError("threshold_years must be positive")
		super().__init__()
		self.threshold_years = threshold_years

	def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
		results: List[Mapping[str, Any]] = []
		for resource in resources:
			updated = iso_datetime(resource.get("lastUpdated"))
			if updated is None:
				meta = resource.get("meta")
				updated = iso_datetime(meta.get("lastUpdated")) if isinstance(meta, Mapping) else None
			reference = reference_date(resource)
			if status(resource) == "active" and updated and reference and updated < reference - timedelta(days=365 * self.threshold_years):
				results.append(finding(self._rule_id, "warning", "timeline", "Active resource has not been updated within the configured stale threshold.", [{"field": "resource.id", "value": resource_id(resource)}, {"field": "lastUpdated", "value": updated.isoformat()}, {"field": "auditReferenceDate", "value": reference.isoformat()}, {"field": "thresholdYears", "value": self.threshold_years}]))
		return results


class RuleTemporal001(_TimelineRule):
	"""Find resources with reversed onset/abatement or period dates."""

	_rule_id = "RULE-TEMPORAL-001"
	_name = "Temporal Ordering Violation"
	_description = "Finds onset or period start dates occurring after their end dates."

	def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
		results: List[Mapping[str, Any]] = []
		for resource in resources:
			pairs = [("onsetDateTime", resource.get("onsetDateTime"), "abatementDateTime", resource.get("abatementDateTime"))]
			period = resource.get("period")
			if isinstance(period, Mapping):
				pairs.append(("period.start", period.get("start"), "period.end", period.get("end")))
			for start_field, start_value, end_field, end_value in pairs:
				start, end = iso_datetime(start_value), iso_datetime(end_value)
				if start and end and start > end:
					results.append(finding(self._rule_id, "warning", "timeline", "Resource date sequence has a start after its end.", [{"field": "resource.id", "value": resource_id(resource)}, {"field": start_field, "value": start_value}, {"field": end_field, "value": end_value}]))
		return results


class RuleLifecycle001(_TimelineRule):
	"""Find prohibited state transitions recorded in resource metadata."""

	_rule_id = "RULE-LIFECYCLE-001"
	_name = "Invalid State Lifecycle Transition"
	_description = "Finds prohibited resource status transitions."

	def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
		results: List[Mapping[str, Any]] = []
		for resource in resources:
			meta = resource.get("meta")
			previous = meta.get("previousStatus") if isinstance(meta, Mapping) else None
			current = status(resource)
			if isinstance(previous, str) and current and previous.lower() in {"cancelled", "entered-in-error"} and current == "active":
				results.append(finding(self._rule_id, "warning", "timeline", "Resource status transitioned from a terminal state to active.", [{"field": "resource.id", "value": resource_id(resource)}, {"field": "previousStatus", "value": previous}, {"field": "currentStatus", "value": current}]))
		return results

