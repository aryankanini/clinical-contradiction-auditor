from __future__ import annotations

import unittest

from module_1_data.pipeline import ingest_batch


class CompletenessValidationTests(unittest.TestCase):
	def test_completeness_validation_unresolved_and_incomplete_states(self) -> None:
		payload = {
			"batch_id": "batch-validate-1",
			"source": "ehr-a",
			"records": [
				{"id": "proc-1", "resourceType": "Procedure", "status": "completed", "subject": {"reference": "Patient/pat-1"}},
			],
		}

		result = ingest_batch(payload)
		state = result.validation_states[0]

		self.assertIn("timestamp", state.incomplete_fields)
		self.assertIn("subject", state.unresolved_links)
		self.assertFalse(state.rule_ready)

	def test_completeness_validation_mixed_batch_states(self) -> None:
		payload = {
			"batch_id": "batch-validate-2",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}},
				{"id": "obs-1", "resourceType": "Observation", "status": "final"},
			],
		}

		result = ingest_batch(payload)

		self.assertEqual(len(result.validation_states), 2)
		self.assertTrue(any(state.generic_incompleteness for state in result.validation_states))


if __name__ == "__main__":
	unittest.main()
