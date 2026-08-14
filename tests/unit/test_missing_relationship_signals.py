from __future__ import annotations

import unittest

from module_1_data.pipeline import ingest_batch


class MissingRelationshipSignalTests(unittest.TestCase):
	def test_missing_relationship_signals_generic_incompleteness_not_governed(self) -> None:
		payload = {
			"batch_id": "batch-signal-1",
			"source": "ehr-a",
			"records": [
				{"id": "obs-1", "resourceType": "Observation", "status": "final"},
			],
		}

		result = ingest_batch(payload)

		self.assertTrue(any(state.generic_incompleteness for state in result.validation_states))
		self.assertEqual(len(result.governed_signals), 0)

	def test_missing_relationship_signals_respect_explicit_rule_expectations(self) -> None:
		payload = {
			"batch_id": "batch-signal-2",
			"source": "ehr-a",
			"records": [
				{"id": "condition-1", "resourceType": "Condition", "status": "active", "recordedDate": "2026-08-12T10:00:00Z"},
			],
		}

		result = ingest_batch(payload)

		self.assertEqual(result.governed_signals[0]["relationship_field"], "encounter")
		self.assertTrue(result.governed_signals[0]["audit_only_note"].startswith("Audit-only"))


if __name__ == "__main__":
	unittest.main()
