from __future__ import annotations

import unittest
from datetime import timedelta

from module_2_audit_engine.rules.timeline_rules import expected_relationships_for
from module_4_api_ui.backend.audit_engine.port import AuditEnginePort
from module_4_api_ui.backend.audit_engine.stub_engine import StubAuditEngine
from module_4_api_ui.backend.constants import (
	OUTCOME_CONTRADICTION_CONFIRMED,
	OUTCOME_GAP_CONFIRMED,
	OUTCOME_NON_ACTIONABLE,
	FINDING_TYPE_CONTRADICTION,
	FINDING_TYPE_MISSING_RELATIONSHIP,
	FINDING_TYPE_STALE_STATE,
	FINDING_TYPE_TIMELINE_VIOLATION,
)
from tests.unit.api_test_base import FIXED_NOW, audit_input, reference


RULE_PACK: dict = {"stale_after_days": 365}


def _rule_ids(result) -> set[str]:
	return {finding.rule_id for finding in result.findings}


class PortConformanceTests(unittest.TestCase):
	def test_stub_engine_satisfies_the_audit_engine_port(self) -> None:
		self.assertIsInstance(StubAuditEngine(), AuditEnginePort)

	def test_stub_engine_declares_itself_a_placeholder(self) -> None:
		self.assertTrue(StubAuditEngine().is_placeholder)


class ContradictionRuleTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = StubAuditEngine(as_of=FIXED_NOW)

	def test_active_careplan_referencing_stopped_medication_is_flagged(self) -> None:
		resources = [
			audit_input(
				"cp-1",
				"CarePlan",
				"active",
				references={"basedOn": reference("mr-1")},
				timestamps={"created": "2026-08-01T00:00:00Z"},
			),
			audit_input(
				"mr-1",
				"MedicationRequest",
				"stopped",
				family="Medication",
				timestamps={"authoredOn": "2026-08-01T00:00:00Z"},
			),
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("CONTRA-CAREPLAN-MEDREQ-STATUS", _rule_ids(result))
		finding = next(
			f for f in result.findings if f.rule_id == "CONTRA-CAREPLAN-MEDREQ-STATUS"
		)
		self.assertEqual(finding.finding_type, FINDING_TYPE_CONTRADICTION)
		self.assertEqual(finding.severity, "critical")
		self.assertEqual(len(finding.evidence), 2)

	def test_active_careplan_referencing_active_medication_is_not_flagged(self) -> None:
		resources = [
			audit_input(
				"cp-1",
				"CarePlan",
				"active",
				references={"basedOn": reference("mr-1")},
				timestamps={"created": "2026-08-01T00:00:00Z"},
			),
			audit_input(
				"mr-1",
				"MedicationRequest",
				"active",
				family="Medication",
				timestamps={"authoredOn": "2026-08-01T00:00:00Z"},
			),
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertNotIn("CONTRA-CAREPLAN-MEDREQ-STATUS", _rule_ids(result))

	def test_active_condition_on_cancelled_encounter_is_flagged(self) -> None:
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"active",
				references={"encounter": reference("enc-1")},
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
			),
			audit_input(
				"enc-1",
				"Encounter",
				"cancelled",
				timestamps={"period.start": "2026-08-01T00:00:00Z"},
			),
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("CONTRA-CONDITION-ENCOUNTER-STATE", _rule_ids(result))


class StaleStateRuleTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = StubAuditEngine(as_of=FIXED_NOW)

	def test_open_status_older_than_threshold_is_flagged(self) -> None:
		old = (FIXED_NOW - timedelta(days=400)).isoformat()
		resources = [audit_input("cond-1", "Condition", "active", timestamps={"recordedDate": old})]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("STALE-STATUS-OPEN", _rule_ids(result))
		finding = next(f for f in result.findings if f.rule_id == "STALE-STATUS-OPEN")
		self.assertEqual(finding.finding_type, FINDING_TYPE_STALE_STATE)

	def test_open_status_within_threshold_is_not_flagged(self) -> None:
		recent = (FIXED_NOW - timedelta(days=30)).isoformat()
		resources = [
			audit_input("cond-1", "Condition", "active", timestamps={"recordedDate": recent})
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertNotIn("STALE-STATUS-OPEN", _rule_ids(result))

	def test_closed_status_is_never_stale(self) -> None:
		old = (FIXED_NOW - timedelta(days=4000)).isoformat()
		resources = [
			audit_input("cond-1", "Condition", "resolved", timestamps={"recordedDate": old})
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertNotIn("STALE-STATUS-OPEN", _rule_ids(result))

	def test_unparseable_timestamp_is_counted_as_skipped(self) -> None:
		resources = [
			audit_input("cond-1", "Condition", "active", timestamps={"recordedDate": "not-a-date"})
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertEqual(result.skipped_record_count, 1)
		self.assertNotIn("STALE-STATUS-OPEN", _rule_ids(result))


class TimelineRuleTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = StubAuditEngine(as_of=FIXED_NOW)

	def test_future_timestamp_is_flagged(self) -> None:
		future = (FIXED_NOW + timedelta(days=5)).isoformat()
		resources = [
			audit_input("obs-1", "Observation", "final", timestamps={"effectiveDateTime": future})
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("TIMELINE-FUTURE-EVENT", _rule_ids(result))
		finding = next(f for f in result.findings if f.rule_id == "TIMELINE-FUTURE-EVENT")
		self.assertEqual(finding.finding_type, FINDING_TYPE_TIMELINE_VIOLATION)

	def test_event_dated_before_its_encounter_is_flagged(self) -> None:
		resources = [
			audit_input(
				"obs-1",
				"Observation",
				"final",
				timestamps={"effectiveDateTime": "2026-01-01T00:00:00Z"},
				references={"encounter": reference("enc-1")},
			),
			audit_input(
				"enc-1",
				"Encounter",
				"finished",
				timestamps={"period.start": "2026-06-01T00:00:00Z"},
			),
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("TIMELINE-EVENT-PRECEDES-ENCOUNTER", _rule_ids(result))

	def test_event_dated_after_its_encounter_is_not_flagged(self) -> None:
		resources = [
			audit_input(
				"obs-1",
				"Observation",
				"final",
				timestamps={"effectiveDateTime": "2026-07-01T00:00:00Z"},
				references={"encounter": reference("enc-1")},
			),
			audit_input(
				"enc-1",
				"Encounter",
				"finished",
				timestamps={"period.start": "2026-06-01T00:00:00Z"},
			),
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertNotIn("TIMELINE-EVENT-PRECEDES-ENCOUNTER", _rule_ids(result))


class RelationshipRuleTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = StubAuditEngine(as_of=FIXED_NOW)

	def test_missing_rule_expected_reference_is_flagged(self) -> None:
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"resolved",
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
				references={},
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("REL-CONDITION-ENCOUNTER", _rule_ids(result))
		finding = next(f for f in result.findings if f.rule_id == "REL-CONDITION-ENCOUNTER")
		self.assertEqual(finding.finding_type, FINDING_TYPE_MISSING_RELATIONSHIP)

	def test_rule_ids_match_the_module_2_relationship_catalogue(self) -> None:
		"""The stub reuses module 2's catalogue, so rule IDs match what module 1 persists."""
		self.assertEqual(expected_relationships_for("Condition"), ["encounter"])

		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"resolved",
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
			)
		]
		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("REL-CONDITION-ENCOUNTER", _rule_ids(result))

	def test_unresolved_reference_state_is_flagged(self) -> None:
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"resolved",
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
				references={"encounter": reference("enc-9", state="unresolved")},
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("REL-CONDITION-ENCOUNTER", _rule_ids(result))

	def test_resolved_reference_is_not_flagged(self) -> None:
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"resolved",
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
				references={"encounter": reference("enc-1")},
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertNotIn("REL-CONDITION-ENCOUNTER", _rule_ids(result))

	def test_resource_with_no_expected_relationships_is_not_flagged(self) -> None:
		self.assertEqual(expected_relationships_for("Encounter"), [])

		resources = [
			audit_input(
				"enc-1",
				"Encounter",
				"finished",
				timestamps={"period.start": "2026-08-01T00:00:00Z"},
			)
		]
		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertEqual(
			[f for f in result.findings if f.finding_type == FINDING_TYPE_MISSING_RELATIONSHIP],
			[],
		)


class AuditOnlyBoundaryTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = StubAuditEngine(as_of=FIXED_NOW)
		self.old = (FIXED_NOW - timedelta(days=400)).isoformat()

	def test_finding_on_record_with_incomplete_fields_is_marked_non_actionable(self) -> None:
		"""UC-002 ext 2a: incomplete data is recorded but must not read as confirmed."""
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"active",
				timestamps={"recordedDate": self.old},
				incomplete_fields=["status"],
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		stale = next(f for f in result.findings if f.rule_id == "STALE-STATUS-OPEN")
		self.assertEqual(stale.audit_outcome, OUTCOME_NON_ACTIONABLE)

	def test_non_actionable_finding_is_still_emitted(self) -> None:
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"active",
				timestamps={"recordedDate": self.old},
				incomplete_fields=["status"],
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		self.assertIn("STALE-STATUS-OPEN", _rule_ids(result))

	def test_unresolved_subject_alone_does_not_block_actionability(self) -> None:
		"""A ``subject`` pointing at an out-of-batch Patient is normal, not a defect.

		Module 1 clears ``rule_ready`` for any unresolved reference, and in a
		resource-scoped batch ``subject`` never resolves. Keying non-actionability off
		that would make almost every finding untriageable.
		"""
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"active",
				timestamps={"recordedDate": self.old},
				rule_ready=False,
				unresolved_links=["subject"],
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		stale = next(f for f in result.findings if f.rule_id == "STALE-STATUS-OPEN")
		self.assertEqual(stale.audit_outcome, OUTCOME_CONTRADICTION_CONFIRMED)

	def test_relationship_finding_is_confirmed_despite_the_unresolved_link(self) -> None:
		"""For a REL-* rule the unresolved link is the finding itself (FR-005)."""
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"resolved",
				timestamps={"recordedDate": "2026-08-01T00:00:00Z"},
				rule_ready=False,
				unresolved_links=["encounter"],
			)
		]

		result = self.engine.evaluate_batch(resources, RULE_PACK)

		gap = next(f for f in result.findings if f.rule_id == "REL-CONDITION-ENCOUNTER")
		self.assertEqual(gap.audit_outcome, OUTCOME_GAP_CONFIRMED)


class DeterminismTests(unittest.TestCase):
	def test_repeated_evaluation_produces_identical_findings(self) -> None:
		"""FR-012 reproducibility depends on the engine being deterministic."""
		engine = StubAuditEngine(as_of=FIXED_NOW)
		resources = [
			audit_input(
				"cond-1",
				"Condition",
				"active",
				timestamps={"recordedDate": "2020-01-01T00:00:00Z"},
			),
			audit_input(
				"enc-1",
				"Encounter",
				"cancelled",
				timestamps={"period.start": "2026-01-01T00:00:00Z"},
			),
		]

		first = engine.evaluate_batch(resources, RULE_PACK)
		second = engine.evaluate_batch(list(reversed(resources)), RULE_PACK)

		self.assertEqual(first.findings, second.findings)

	def test_evaluated_record_count_matches_input_size(self) -> None:
		engine = StubAuditEngine(as_of=FIXED_NOW)
		resources = [
			audit_input("a", "Observation", "final"),
			audit_input("b", "Observation", "final"),
		]

		result = engine.evaluate_batch(resources, RULE_PACK)

		self.assertEqual(result.evaluated_record_count, 2)

	def test_rule_pack_version_is_reported_on_the_result(self) -> None:
		engine = StubAuditEngine(as_of=FIXED_NOW)

		result = engine.evaluate_batch([], RULE_PACK)

		self.assertEqual(result.rule_pack_version, engine.rule_pack_version)


if __name__ == "__main__":
	unittest.main()
