"""Deterministic contradiction rules for FHIR medication resources."""

from __future__ import annotations

from typing import Any, Mapping

from module_2_audit_engine.deterministic.rule_interface import RuleInterface, RuleMetadata
from module_2_audit_engine.rules._rule_utils import finding, iso_datetime, reference_date, resource_id, resources_of_type, status


class _MedicationRule(RuleInterface):
	_rule_id = ""
	_name = ""
	_description = ""

	def __init__(self) -> None:
		self._metadata = RuleMetadata(self._rule_id, "1.0.0", self._name, self._description, "medication")

	@property
	def metadata(self) -> RuleMetadata:
		return self._metadata


def _medications(resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
	return [resource for resource in resources if resource.get("resourceType") in {"MedicationStatement", "MedicationRequest"}]


def _dose_value(resource: Mapping[str, Any]) -> float | None:
	dosages = resource.get("dosageInstruction")
	if not isinstance(dosages, list):
		return None
	for dosage in dosages:
		if not isinstance(dosage, Mapping):
			continue
		rates = dosage.get("doseAndRate")
		if not isinstance(rates, list):
			continue
		for rate in rates:
			if isinstance(rate, Mapping):
				quantity = rate.get("doseQuantity")
				if isinstance(quantity, Mapping) and isinstance(quantity.get("value"), (int, float)):
					return float(quantity["value"])
	return None


class RuleMedication001(_MedicationRule):
	"""Find active medications whose effective end is before the audit date."""

	_rule_id = "RULE-MED-001"
	_name = "Active Medication Outside Effective Period"
	_description = "Finds active medications with an effective end before the audit date."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		results: list[Mapping[str, Any]] = []
		for medication in _medications(resources):
			period = medication.get("effectivePeriod")
			end = iso_datetime(period.get("end")) if isinstance(period, Mapping) else iso_datetime(medication.get("effectiveDateTime"))
			reference = reference_date(medication)
			if status(medication) == "active" and end and reference and end < reference:
				results.append(finding(self._rule_id, "warning", "medication", "Active medication is outside its effective period.", [{"field": "Medication.id", "value": resource_id(medication)}, {"field": "effectiveEnd", "value": end.isoformat()}, {"field": "auditReferenceDate", "value": reference.isoformat()}]))
		return results


class RuleMedication002(_MedicationRule):
	"""Find medication effective periods with start after end."""

	_rule_id = "RULE-MED-002"
	_name = "Medication Effective Date Ordering"
	_description = "Finds medication effective periods with start after end."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		results: list[Mapping[str, Any]] = []
		for medication in _medications(resources):
			period = medication.get("effectivePeriod")
			if not isinstance(period, Mapping):
				continue
			start, end = iso_datetime(period.get("start")), iso_datetime(period.get("end"))
			if start and end and start > end:
				results.append(finding(self._rule_id, "warning", "medication", "Medication effective period starts after it ends.", [{"field": "Medication.id", "value": resource_id(medication)}, {"field": "effectiveStart", "value": period.get("start")}, {"field": "effectiveEnd", "value": period.get("end")}]))
		return results


class RuleMedication003(_MedicationRule):
	"""Find stopped medications referenced by active plans or requests."""

	_rule_id = "RULE-MED-003"
	_name = "Stopped Medication With Active Reference"
	_description = "Finds stopped medications referenced by active care resources."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		active_references = [resource for resource in resources if resource.get("resourceType") in {"CarePlan", "MedicationRequest"} and status(resource) == "active"]
		return [finding(self._rule_id, "warning", "medication", "Stopped medication has active care references.", [{"field": "Medication.id", "value": resource_id(medication)}, {"field": "activeReferenceCount", "value": len(active_references)}]) for medication in _medications(resources) if status(medication) == "stopped" and active_references]


class RuleMedication004(_MedicationRule):
	"""Find medication entries with zero or negative recorded doses."""

	_rule_id = "RULE-MED-004"
	_name = "Invalid Medication Dose"
	_description = "Finds medication entries with a non-positive dose."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		return [finding(self._rule_id, "warning", "medication", "Medication has a non-positive dose value.", [{"field": "Medication.id", "value": resource_id(medication)}, {"field": "dose", "value": dose}]) for medication in _medications(resources) if (dose := _dose_value(medication)) is not None and dose <= 0]


class RuleMedication005(_MedicationRule):
	"""Find same-code medication entries with the same status."""

	_rule_id = "RULE-MED-005"
	_name = "Duplicate Medication Entries"
	_description = "Finds duplicate medication entries sharing code and status."

	def execute(self, resources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
		medications = _medications(resources)
		results: list[Mapping[str, Any]] = []
		for medication in medications:
			code = medication.get("medicationCodeableConcept")
			duplicates = [candidate for candidate in medications if candidate is not medication and candidate.get("medicationCodeableConcept") == code and status(candidate) == status(medication)]
			if isinstance(code, Mapping) and duplicates:
				results.append(finding(self._rule_id, "info", "medication", "Medication entry matches another entry with the same status.", [{"field": "Medication.id", "value": resource_id(medication)}, {"field": "matchingMedicationIds", "value": [resource_id(candidate) for candidate in duplicates]}]))
		return results
