from __future__ import annotations

import unittest

from module_1_data.pipeline import ingest_batch
from shared.enums.normalization_state import NormalizationState


class NormalizedModelTests(unittest.TestCase):
	def test_normalized_models_preserve_traceability_and_explicit_states(self) -> None:
		payload = {
			"batch_id": "batch-norm-model",
			"source": "ehr-a",
			"records": [
				{
					"id": "enc-1",
					"resourceType": "Encounter",
					"status": "finished",
					"period": {"start": "2026-08-12T10:00:00Z"},
					"subject": {"reference": "Patient/pat-1"},
				},
			],
		}

		result = ingest_batch(payload)
		resource = result.normalized_resources[0]

		self.assertEqual(resource.provenance["source_record_id"], "enc-1")
		self.assertEqual(resource.status.state, NormalizationState.VALID)
		self.assertIn("start", resource.timestamps)
		self.assertEqual(resource.timestamps["start"].state, NormalizationState.VALID)

	def test_normalized_models_mark_missing_values_explicitly(self) -> None:
		payload = {
			"batch_id": "batch-norm-missing",
			"source": "ehr-a",
			"records": [{"id": "obs-1", "resourceType": "Observation"}],
		}

		result = ingest_batch(payload)
		resource = result.normalized_resources[0]

		self.assertEqual(resource.status.state, NormalizationState.MISSING)
		self.assertEqual(resource.primary_timestamp.state, NormalizationState.MISSING)


if __name__ == "__main__":
	unittest.main()
