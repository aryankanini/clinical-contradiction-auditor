"""Deterministic contradiction rules for encounter-family FHIR resources."""

from __future__ import annotations

from typing import Any, Mapping

from module_2_audit_engine.deterministic.rule_interface import RuleInterface, RuleMetadata
from module_2_audit_engine.rules._rule_utils import finding, iso_datetime, reference_date, resource_id, resources_of_type, status


class _ResourceRule(RuleInterface):
	_rule_id = ""
	_name = ""
	_description = ""
	_category = "encounter"

	def __init__(self) -> None:
		self._metadata = RuleMetadata(self._rule_id, "1.0.0", self._name, self._description, self._category)

	@property
	def metadata(self) -> RuleMetadata:
		return self._metadata


class RuleEncounter001(_ResourceRule):
	_rule_id, _name, _description = "RULE-ENC-001", "Encounter Period Ordering", "Finds encounter periods starting after they end."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return _period_order_findings(resources_of_type(resources, "Encounter"), self._metadata, "Encounter")


class RuleEncounter002(_ResourceRule):
	_rule_id, _name, _description = "RULE-ENC-002", "Completed Encounter With Future End", "Finds completed encounters ending after the audit date."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return _completed_future_end(resources_of_type(resources, "Encounter"), self._metadata, "Encounter")


class RuleProcedure001(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-PROC-001", "Completed Procedure Without Date", "Finds completed procedures without a performed date.", "procedure"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return [finding(self._rule_id, "warning", self._category, "Completed procedure has no performed date.", [{"field": "Procedure.id", "value": resource_id(procedure)}, {"field": "status", "value": status(procedure)}]) for procedure in resources_of_type(resources, "Procedure") if status(procedure) == "completed" and not iso_datetime(procedure.get("performedDateTime"))]


class RuleProcedure002(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-PROC-002", "Procedure Period Ordering", "Finds procedure periods starting after they end.", "procedure"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return _period_order_findings(resources_of_type(resources, "Procedure"), self._metadata, "Procedure", "performedPeriod")


class RuleObservation001(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-OBS-001", "Final Observation With Future Date", "Finds final observations effective after the audit date.", "observation"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		results: list[Mapping[str, Any]] = []
		for observation in resources_of_type(resources, "Observation"):
			effective, reference = iso_datetime(observation.get("effectiveDateTime")), reference_date(observation)
			if status(observation) == "final" and effective and reference and effective > reference:
				results.append(finding(self._rule_id, "warning", self._category, "Final observation has an effective date after the audit reference date.", [{"field": "Observation.id", "value": resource_id(observation)}, {"field": "effectiveDateTime", "value": observation.get("effectiveDateTime")}]))
		return results


class RuleObservation002(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-OBS-002", "Observation Without Value", "Finds non-cancelled observations without a value.", "observation"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return [finding(self._rule_id, "warning", self._category, "Non-cancelled observation has no recorded value.", [{"field": "Observation.id", "value": resource_id(observation)}, {"field": "status", "value": status(observation)}]) for observation in resources_of_type(resources, "Observation") if status(observation) != "cancelled" and not any(key.startswith("value") and observation.get(key) is not None for key in observation)]


class RuleCarePlan001(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-CARE-001", "Completed Care Plan With Future End", "Finds completed care plans ending after the audit date.", "careplan"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return _completed_future_end(resources_of_type(resources, "CarePlan"), self._metadata, "CarePlan")


class RuleCarePlan002(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-CARE-002", "Care Plan Period Ordering", "Finds care plan periods starting after they end.", "careplan"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return _period_order_findings(resources_of_type(resources, "CarePlan"), self._metadata, "CarePlan")


class RuleCarePlan003(_ResourceRule):
	_rule_id, _name, _description, _category = "RULE-CARE-003", "Active Care Plan Without Activities", "Finds active care plans with no activities.", "careplan"

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return [finding(self._rule_id, "info", self._category, "Active care plan has no activities.", [{"field": "CarePlan.id", "value": resource_id(plan)}, {"field": "activityCount", "value": 0}]) for plan in resources_of_type(resources, "CarePlan") if status(plan) == "active" and not plan.get("activity")]


def _period_order_findings(resources: list[Mapping[str, Any]], metadata: RuleMetadata, label: str, period_key: str = "period") -> list[Mapping[str, Any]]:
	results: list[Mapping[str, Any]] = []
	for resource in resources:
		period = resource.get(period_key)
		if not isinstance(period, Mapping):
			continue
		start, end = iso_datetime(period.get("start")), iso_datetime(period.get("end"))
		if start and end and start > end:
			results.append(finding(metadata.rule_id, "warning", metadata.category, f"{label} period starts after it ends.", [{"field": f"{label}.id", "value": resource_id(resource)}, {"field": "period.start", "value": period.get("start")}, {"field": "period.end", "value": period.get("end")}]))
	return results


def _completed_future_end(resources: list[Mapping[str, Any]], metadata: RuleMetadata, label: str) -> list[Mapping[str, Any]]:
	results: list[Mapping[str, Any]] = []
	for resource in resources:
		period = resource.get("period")
		end = iso_datetime(period.get("end")) if isinstance(period, Mapping) else None
		reference = reference_date(resource)
		if status(resource) == "completed" and end and reference and end > reference:
			results.append(finding(metadata.rule_id, "warning", metadata.category, f"Completed {label.lower()} has a period end after the audit reference date.", [{"field": f"{label}.id", "value": resource_id(resource)}, {"field": "period.end", "value": end.isoformat()}]))
	return results
