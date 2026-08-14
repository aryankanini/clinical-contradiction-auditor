from __future__ import annotations

import unittest

from module_1_data.pipeline import ingest_batch
from shared.enums.normalization_state import NormalizationState


class NormalizationLogicTests(unittest.TestCase):
	def test_normalization_logic_status_timestamp_reference_deterministic(self) -> None:
		payload = {
			"batch_id": "batch-norm-logic",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}},
			],
		}

		result = ingest_batch(payload)
		resource = result.normalized_resources[0]

		self.assertEqual(resource.status.value, "finished")
		self.assertEqual(resource.timestamps["start"].value, "2026-08-12T10:00:00Z")
		self.assertEqual(resource.references["subject"].state, NormalizationState.UNRESOLVED)

	def test_normalization_logic_marks_ambiguous_timestamps(self) -> None:
		payload = {
			"batch_id": "batch-norm-ambiguous",
			"source": "ehr-a",
			"records": [
				{
					"id": "obs-1",
					"resourceType": "Observation",
					"status": "final",
					"effectiveDateTime": "2026-08-12T10:00:00Z",
					"issued": "2026-08-12T11:00:00Z",
				},
			],
		}

		result = ingest_batch(payload)
		resource = result.normalized_resources[0]

		self.assertEqual(resource.timestamps["issued"].state, NormalizationState.AMBIGUOUS)


if __name__ == "__main__":
	unittest.main()
