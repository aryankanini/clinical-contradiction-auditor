"""Deterministic contradiction rules for FHIR Condition resources."""

from __future__ import annotations

from typing import Any, Mapping

from module_2_audit_engine.deterministic.rule_interface import RuleInterface, RuleMetadata
from module_2_audit_engine.rules._rule_utils import finding, iso_datetime, reference_date, resource_id, resources_of_type, status


class _ConditionRule(RuleInterface):
	_rule_id = ""
	_name = ""
	_description = ""

	def __init__(self) -> None:
		self._metadata = RuleMetadata(self._rule_id, "1.0.0", self._name, self._description, "diagnosis")

	@property
	def metadata(self) -> RuleMetadata:
		return self._metadata


class RuleCondition001(_ConditionRule):
	"""Find active conditions whose onset is after an explicit audit reference date."""

	_rule_id = "RULE-COND-001"
	_name = "Active Condition With Future Onset"
	_description = "Finds active conditions with an onset after the audit reference date."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		results: list[Mapping[str, Any]] = []
		for condition in resources_of_type(resources, "Condition"):
			onset = iso_datetime(condition.get("onsetDateTime"))
			reference = reference_date(condition)
			if status(condition) == "active" and onset and reference and onset > reference:
				results.append(finding(self._rule_id, "warning", "diagnosis", "Active condition has an onset after the audit reference date.", [{"field": "Condition.id", "value": resource_id(condition)}, {"field": "onsetDateTime", "value": condition.get("onsetDateTime")}, {"field": "auditReferenceDate", "value": condition.get("meta", {}).get("auditReferenceDate")}]))
		return results


class RuleCondition002(_ConditionRule):
	"""Find conditions whose onset follows their abatement."""

	_rule_id = "RULE-COND-002"
	_name = "Condition Onset And Abatement Ordering"
	_description = "Finds conditions with onset after abatement."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		results: list[Mapping[str, Any]] = []
		for condition in resources_of_type(resources, "Condition"):
			onset = iso_datetime(condition.get("onsetDateTime"))
			abatement = iso_datetime(condition.get("abatementDateTime"))
			if onset and abatement and onset > abatement:
				results.append(finding(self._rule_id, "warning", "diagnosis", "Condition onset is after its abatement date.", [{"field": "Condition.id", "value": resource_id(condition)}, {"field": "onsetDateTime", "value": condition.get("onsetDateTime")}, {"field": "abatementDateTime", "value": condition.get("abatementDateTime")}]))
		return results


class RuleCondition003(_ConditionRule):
	"""Find active conditions that include an abatement date."""

	_rule_id = "RULE-COND-003"
	_name = "Active Condition With Abatement"
	_description = "Finds active conditions that also contain an abatement date."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return [finding(self._rule_id, "warning", "diagnosis", "Active condition includes an abatement date.", [{"field": "Condition.id", "value": resource_id(condition)}, {"field": "status", "value": status(condition)}, {"field": "abatementDateTime", "value": condition.get("abatementDateTime")}]) for condition in resources_of_type(resources, "Condition") if status(condition) == "active" and iso_datetime(condition.get("abatementDateTime"))]


class RuleCondition004(_ConditionRule):
	"""Find entered-in-error conditions duplicated by another condition code."""

	_rule_id = "RULE-COND-004"
	_name = "Entered In Error Condition With Duplicate"
	_description = "Finds entered-in-error conditions with another condition of the same code."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		conditions = resources_of_type(resources, "Condition")
		results: list[Mapping[str, Any]] = []
		for condition in conditions:
			code = condition.get("code")
			if status(condition) != "entered-in-error" or not isinstance(code, Mapping):
				continue
			duplicate_count = sum(1 for candidate in conditions if candidate is not condition and candidate.get("code") == code)
			if duplicate_count:
				results.append(finding(self._rule_id, "critical", "diagnosis", "Entered-in-error condition has matching condition entries.", [{"field": "Condition.id", "value": resource_id(condition)}, {"field": "matchingConditionCount", "value": duplicate_count}]))
		return results
