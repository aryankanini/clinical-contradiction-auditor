from __future__ import annotations

import unittest

from module_4_api_ui.backend.constants import (
	OUTCOME_CONTRADICTION_CONFIRMED,
	OUTCOME_NON_ACTIONABLE,
)
from module_4_api_ui.backend.services.severity_policy import (
	assign_priority,
	assign_severity,
	base_severity_for_rule,
)


class BaseSeverityTests(unittest.TestCase):
	def test_careplan_medication_contradiction_is_critical(self) -> None:
		self.assertEqual(base_severity_for_rule("CONTRA-CAREPLAN-MEDREQ-STATUS"), "critical")

	def test_specific_rule_prefix_wins_over_family_prefix(self) -> None:
		"""CONTRA- maps to high, but the longer specific key must take precedence."""
		self.assertEqual(base_severity_for_rule("CONTRA-CAREPLAN-MEDREQ-STATUS"), "critical")
		self.assertEqual(base_severity_for_rule("CONTRA-SOMETHING-ELSE"), "high")

	def test_parameterised_relationship_rule_resolves_by_prefix(self) -> None:
		self.assertEqual(base_severity_for_rule("REL-CONDITION-ENCOUNTER"), "medium")

	def test_unknown_rule_defaults_to_medium(self) -> None:
		self.assertEqual(base_severity_for_rule("NOT-A-REAL-RULE"), "medium")


class SeverityEscalationTests(unittest.TestCase):
	def test_high_risk_family_escalates_medium_to_high(self) -> None:
		severity = assign_severity(
			"REL-CONDITION-ENCOUNTER", ["Condition"], OUTCOME_CONTRADICTION_CONFIRMED
		)

		self.assertEqual(severity, "high")

	def test_low_risk_family_keeps_base_severity(self) -> None:
		severity = assign_severity(
			"REL-OBSERVATION-SUBJECT", ["Observation"], OUTCOME_CONTRADICTION_CONFIRMED
		)

		self.assertEqual(severity, "medium")

	def test_escalation_never_downgrades_a_critical_rule(self) -> None:
		severity = assign_severity(
			"CONTRA-CAREPLAN-MEDREQ-STATUS",
			["CarePlan", "Medication"],
			OUTCOME_CONTRADICTION_CONFIRMED,
		)

		self.assertEqual(severity, "critical")


class PriorityTests(unittest.TestCase):
	def test_critical_severity_maps_to_p1(self) -> None:
		self.assertEqual(assign_priority("critical", OUTCOME_CONTRADICTION_CONFIRMED, 1), "p1")

	def test_low_severity_maps_to_p4(self) -> None:
		self.assertEqual(assign_priority("low", OUTCOME_CONTRADICTION_CONFIRMED, 1), "p4")

	def test_cross_family_finding_is_upgraded_one_step(self) -> None:
		single = assign_priority("medium", OUTCOME_CONTRADICTION_CONFIRMED, 1)
		cross = assign_priority("medium", OUTCOME_CONTRADICTION_CONFIRMED, 2)

		self.assertEqual(single, "p3")
		self.assertEqual(cross, "p2")

	def test_non_actionable_finding_is_downgraded_one_step(self) -> None:
		actionable = assign_priority("high", OUTCOME_CONTRADICTION_CONFIRMED, 1)
		non_actionable = assign_priority("high", OUTCOME_NON_ACTIONABLE, 1)

		self.assertEqual(actionable, "p2")
		self.assertEqual(non_actionable, "p3")

	def test_upgrade_clamps_at_p1(self) -> None:
		self.assertEqual(assign_priority("critical", OUTCOME_CONTRADICTION_CONFIRMED, 3), "p1")

	def test_downgrade_clamps_at_p4(self) -> None:
		self.assertEqual(assign_priority("low", OUTCOME_NON_ACTIONABLE, 1), "p4")

	def test_opposing_adjustments_cancel_out(self) -> None:
		"""Cross-family upgrade and non-actionable downgrade net to no change."""
		self.assertEqual(assign_priority("medium", OUTCOME_NON_ACTIONABLE, 2), "p3")


if __name__ == "__main__":
	unittest.main()
