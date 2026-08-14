from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from module_1_data.pipeline import ingest_batch, reconstruct_ingest_output, reconstruct_ingest_output_from_path


class ReplayArtifactTests(unittest.TestCase):
	def test_replay_artifacts_reconstruct_snapshots(self) -> None:
		payload = {
			"batch_id": "batch-replay-1",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}},
			],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			result = ingest_batch(payload, artifact_dir=temp_dir)
			reconstructed = reconstruct_ingest_output(result.replay_artifact)

			self.assertEqual(reconstructed[0]["record_id"], "enc-1")
			self.assertIn("status", reconstructed[0])
			self.assertTrue(result.replay_artifact.storage_path)
			self.assertTrue(Path(result.replay_artifact.storage_path).exists())
			from_path = reconstruct_ingest_output_from_path(result.replay_artifact.storage_path)
			self.assertEqual(from_path[0]["record_id"], "enc-1")

	def test_replay_artifacts_preserve_partial_failure_fidelity(self) -> None:
		payload = {
			"batch_id": "batch-replay-2",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}},
				{"resourceType": "Observation"},
			],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			result = ingest_batch(payload, artifact_dir=temp_dir)

			self.assertEqual(len(result.replay_artifact.quarantined_records), 1)
			self.assertEqual(result.replay_artifact.provenance_id, result.provenance.provenance_id)


if __name__ == "__main__":
	unittest.main()
