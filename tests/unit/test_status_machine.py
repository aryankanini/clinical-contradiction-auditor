from __future__ import annotations

import unittest

from module_4_api_ui.backend.errors import IllegalTransitionError
from module_4_api_ui.backend.services import status_machine


class LegalTransitionTests(unittest.TestCase):
	def test_new_to_under_review_as_steward_is_allowed(self) -> None:
		status_machine.assert_transition_allowed("new", "under_review", "steward")

	def test_under_review_to_accepted_as_steward_is_allowed(self) -> None:
		status_machine.assert_transition_allowed("under_review", "accepted", "steward")

	def test_accepted_to_in_remediation_with_prerequisites_is_allowed(self) -> None:
		status_machine.assert_transition_allowed(
			"accepted",
			"in_remediation",
			"steward",
			has_approved_resolution=True,
			has_assignment=True,
		)

	def test_remediated_to_closed_as_compliance_is_allowed(self) -> None:
		status_machine.assert_transition_allowed("remediated", "closed", "compliance")


class IllegalTransitionTests(unittest.TestCase):
	def test_new_directly_to_closed_raises(self) -> None:
		with self.assertRaises(IllegalTransitionError) as ctx:
			status_machine.assert_transition_allowed("new", "closed", "steward")

		self.assertEqual(ctx.exception.code, "illegal_transition")

	def test_transition_out_of_terminal_status_raises(self) -> None:
		with self.assertRaises(IllegalTransitionError):
			status_machine.assert_transition_allowed("closed", "under_review", "steward")

	def test_unknown_target_status_raises(self) -> None:
		with self.assertRaises(IllegalTransitionError):
			status_machine.assert_transition_allowed("new", "banana", "steward")

	def test_analyst_cannot_accept_a_finding(self) -> None:
		with self.assertRaises(IllegalTransitionError) as ctx:
			status_machine.assert_transition_allowed("under_review", "accepted", "analyst")

		self.assertEqual(ctx.exception.code, "forbidden_transition")

	def test_in_remediation_without_approved_resolution_raises(self) -> None:
		"""FR-009: no downstream state change on AI output alone."""
		with self.assertRaises(IllegalTransitionError) as ctx:
			status_machine.assert_transition_allowed(
				"accepted",
				"in_remediation",
				"steward",
				has_approved_resolution=False,
				has_assignment=True,
			)

		self.assertEqual(ctx.exception.code, "resolution_approval_required")
		self.assertIn("approved_resolution", ctx.exception.context["missing"])

	def test_in_remediation_without_assignment_raises(self) -> None:
		with self.assertRaises(IllegalTransitionError) as ctx:
			status_machine.assert_transition_allowed(
				"accepted",
				"in_remediation",
				"steward",
				has_approved_resolution=True,
				has_assignment=False,
			)

		self.assertIn("assignment", ctx.exception.context["missing"])


class AllowedTransitionListingTests(unittest.TestCase):
	def test_allowed_transitions_excludes_targets_the_role_cannot_reach(self) -> None:
		steward = status_machine.allowed_transitions_for("under_review", "steward")
		analyst = status_machine.allowed_transitions_for("under_review", "analyst")

		self.assertIn("accepted", steward)
		self.assertNotIn("accepted", analyst)
		self.assertIn("escalated", analyst)

	def test_allowed_transitions_hides_remediation_until_prerequisites_met(self) -> None:
		without = status_machine.allowed_transitions_for("accepted", "steward")
		with_prereqs = status_machine.allowed_transitions_for(
			"accepted",
			"steward",
			has_approved_resolution=True,
			has_assignment=True,
		)

		self.assertNotIn("in_remediation", without)
		self.assertIn("in_remediation", with_prereqs)

	def test_terminal_status_offers_no_transitions(self) -> None:
		self.assertEqual(status_machine.allowed_transitions_for("closed", "steward"), [])


class TransitionPathTests(unittest.TestCase):
	def test_triage_from_new_walks_through_under_review(self) -> None:
		self.assertEqual(status_machine.path_from("new", "accepted"), ("under_review", "accepted"))

	def test_triage_from_under_review_is_a_single_step(self) -> None:
		self.assertEqual(status_machine.path_from("under_review", "accepted"), ("accepted",))


class StatusTableIntegrityTests(unittest.TestCase):
	def test_every_transition_target_is_a_known_status(self) -> None:
		for source, targets in status_machine.STATUS_TRANSITIONS.items():
			for target in targets:
				self.assertIn(target, status_machine.ALL_STATUSES, f"{source} -> {target}")

	def test_every_reachable_status_has_a_role_mapping(self) -> None:
		for source, targets in status_machine.STATUS_TRANSITIONS.items():
			for target in targets:
				self.assertIn(
					target,
					status_machine.ROLES_BY_TARGET_STATUS,
					f"no role may reach '{target}' (from '{source}')",
				)

	def test_terminal_statuses_have_no_outbound_transitions(self) -> None:
		self.assertEqual(status_machine.STATUS_TRANSITIONS["closed"], frozenset())
		self.assertEqual(status_machine.STATUS_TRANSITIONS["closed_no_action"], frozenset())


if __name__ == "__main__":
	unittest.main()
