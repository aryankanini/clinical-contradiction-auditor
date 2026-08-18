from __future__ import annotations

from typing import Any, Callable, Mapping

import pytest

from tests.unit.test_contradiction_rules import RULE_CLASSES


RuleCase = tuple[type[Any], Callable[[], list[Mapping[str, Any]]]]


def _reference_meta() -> Mapping[str, str]:
	return {"auditReferenceDate": "2026-08-17T00:00:00Z"}


RULE_CASES: list[RuleCase] = [
	(RULE_CLASSES[0], lambda: [{"resourceType": "Condition", "id": "1", "clinicalStatus": {"text": "active"}, "onsetDateTime": "2026-08-18T00:00:00Z", "meta": _reference_meta()}]),
	(RULE_CLASSES[1], lambda: [{"resourceType": "Condition", "id": "1", "onsetDateTime": "2026-08-18T00:00:00Z", "abatementDateTime": "2026-08-16T00:00:00Z"}]),
	(RULE_CLASSES[2], lambda: [{"resourceType": "Condition", "id": "1", "clinicalStatus": {"text": "active"}, "abatementDateTime": "2026-08-16T00:00:00Z"}]),
	(RULE_CLASSES[3], lambda: [{"resourceType": "Condition", "id": "1", "status": "entered-in-error", "code": {"text": "x"}}, {"resourceType": "Condition", "id": "2", "code": {"text": "x"}}]),
	(RULE_CLASSES[4], lambda: [{"resourceType": "MedicationStatement", "id": "1", "status": "active", "effectivePeriod": {"end": "2026-08-16T00:00:00Z"}, "meta": _reference_meta()}]),
	(RULE_CLASSES[5], lambda: [{"resourceType": "MedicationStatement", "id": "1", "effectivePeriod": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}}]),
	(RULE_CLASSES[6], lambda: [{"resourceType": "MedicationStatement", "id": "1", "status": "stopped"}, {"resourceType": "CarePlan", "id": "2", "status": "active"}]),
	(RULE_CLASSES[7], lambda: [{"resourceType": "MedicationStatement", "id": "1", "dosageInstruction": [{"doseAndRate": [{"doseQuantity": {"value": 0}}]}]}]),
	(RULE_CLASSES[8], lambda: [{"resourceType": "MedicationStatement", "id": "1", "status": "active", "medicationCodeableConcept": {"text": "x"}}, {"resourceType": "MedicationStatement", "id": "2", "status": "active", "medicationCodeableConcept": {"text": "x"}}]),
	(RULE_CLASSES[9], lambda: [{"resourceType": "Encounter", "id": "1", "period": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}}]),
	(RULE_CLASSES[10], lambda: [{"resourceType": "Encounter", "id": "1", "status": "completed", "period": {"end": "2026-08-18T00:00:00Z"}, "meta": _reference_meta()}]),
	(RULE_CLASSES[11], lambda: [{"resourceType": "Procedure", "id": "1", "status": "completed"}]),
	(RULE_CLASSES[12], lambda: [{"resourceType": "Procedure", "id": "1", "performedPeriod": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}}]),
	(RULE_CLASSES[13], lambda: [{"resourceType": "Observation", "id": "1", "status": "final", "effectiveDateTime": "2026-08-18T00:00:00Z", "meta": _reference_meta()}]),
	(RULE_CLASSES[14], lambda: [{"resourceType": "Observation", "id": "1", "status": "final"}]),
	(RULE_CLASSES[15], lambda: [{"resourceType": "CarePlan", "id": "1", "status": "completed", "period": {"end": "2026-08-18T00:00:00Z"}, "meta": _reference_meta()}]),
	(RULE_CLASSES[16], lambda: [{"resourceType": "CarePlan", "id": "1", "period": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}}]),
	(RULE_CLASSES[17], lambda: [{"resourceType": "CarePlan", "id": "1", "status": "active", "activity": []}]),
]


@pytest.mark.parametrize("rule_class,contradiction", RULE_CASES)
def test_rule_contradiction_emits_finding(rule_class: type[Any], contradiction: Callable[[], list[Mapping[str, Any]]]) -> None:
	findings = rule_class().execute(contradiction())
	assert findings
	assert all(finding["rule_id"] == rule_class().metadata.rule_id for finding in findings)


@pytest.mark.parametrize("rule_class,_", RULE_CASES)
def test_rule_valid_patient_input_emits_no_finding(rule_class: type[Any], _: Callable[[], list[Mapping[str, Any]]]) -> None:
	assert rule_class().execute([{"resourceType": "Patient", "id": "patient-1"}]) == []


@pytest.mark.parametrize("rule_class,_", RULE_CASES)
def test_rule_missing_fields_are_handled(rule_class: type[Any], _: Callable[[], list[Mapping[str, Any]]]) -> None:
	assert rule_class().execute([]) == []