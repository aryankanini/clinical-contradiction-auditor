from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from module_2_audit_engine.deterministic.rule_interface import RuleInterface
from module_2_audit_engine.rules.diagnosis_rules import RuleCondition001, RuleCondition002, RuleCondition003, RuleCondition004
from module_2_audit_engine.rules.encounter_rules import RuleCarePlan001, RuleCarePlan002, RuleCarePlan003, RuleEncounter001, RuleEncounter002, RuleObservation001, RuleObservation002, RuleProcedure001, RuleProcedure002
from module_2_audit_engine.rules.medication_rules import RuleMedication001, RuleMedication002, RuleMedication003, RuleMedication004, RuleMedication005


RULE_CLASSES: list[type[RuleInterface]] = [RuleCondition001, RuleCondition002, RuleCondition003, RuleCondition004, RuleMedication001, RuleMedication002, RuleMedication003, RuleMedication004, RuleMedication005, RuleEncounter001, RuleEncounter002, RuleProcedure001, RuleProcedure002, RuleObservation001, RuleObservation002, RuleCarePlan001, RuleCarePlan002, RuleCarePlan003]


def test_rule_metadata_covers_all_contradiction_rule_ids() -> None:
	expected_ids = {f"RULE-COND-{index:03d}" for index in range(1, 5)} | {f"RULE-MED-{index:03d}" for index in range(1, 6)} | {"RULE-ENC-001", "RULE-ENC-002", "RULE-PROC-001", "RULE-PROC-002", "RULE-OBS-001", "RULE-OBS-002", "RULE-CARE-001", "RULE-CARE-002", "RULE-CARE-003"}

	assert {rule_class().metadata.rule_id for rule_class in RULE_CLASSES} == expected_ids
	assert all(rule_class().execute([]) == [] for rule_class in RULE_CLASSES)


def test_rules_detect_representative_contradictions_deterministically() -> None:
	resources: list[Mapping[str, Any]] = [
		{"resourceType": "Condition", "id": "condition-1", "clinicalStatus": {"text": "active"}, "onsetDateTime": "2026-08-18T00:00:00Z", "abatementDateTime": "2026-08-16T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "MedicationStatement", "id": "medication-1", "status": "active", "effectivePeriod": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}, "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "Encounter", "id": "encounter-1", "status": "completed", "period": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}, "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "Procedure", "id": "procedure-1", "status": "completed", "performedPeriod": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}},
		{"resourceType": "Observation", "id": "observation-1", "status": "final", "effectiveDateTime": "2026-08-18T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "CarePlan", "id": "care-plan-1", "status": "completed", "period": {"start": "2026-08-18T00:00:00Z", "end": "2026-08-16T00:00:00Z"}, "activity": [], "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
		{"resourceType": "CarePlan", "id": "care-plan-2", "status": "completed", "period": {"start": "2026-08-16T00:00:00Z", "end": "2026-08-18T00:00:00Z"}, "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}},
	]

	first_run = [finding for rule_class in RULE_CLASSES for finding in rule_class().execute(resources)]
	second_run = [finding for rule_class in RULE_CLASSES for finding in rule_class().execute(resources)]

	assert first_run == second_run
	assert {finding["rule_id"] for finding in first_run} >= {"RULE-COND-001", "RULE-COND-002", "RULE-COND-003", "RULE-MED-001", "RULE-MED-002", "RULE-ENC-001", "RULE-PROC-001", "RULE-PROC-002", "RULE-OBS-001", "RULE-OBS-002", "RULE-CARE-001", "RULE-CARE-002"}


def test_rule_pack_defines_each_rule_class() -> None:
	path = Path("data/rule_packs/contradiction_rules_v1.yaml")
	with path.open(encoding="utf-8") as rule_pack_file:
		pack = yaml.safe_load(rule_pack_file)

	assert {definition["rule_id"] for definition in pack["rules"]} == {rule_class().metadata.rule_id for rule_class in RULE_CLASSES}