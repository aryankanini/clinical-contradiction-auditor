from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from module_1_data.pipeline import ingest_batch


class IngestProvenanceTests(unittest.TestCase):
	def test_ingest_provenance_captures_counts_and_validation(self) -> None:
		payload = {
			"batch_id": "batch-prov-1",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}},
			],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			result = ingest_batch(payload, artifact_dir=temp_dir)

			self.assertEqual(result.provenance.batch_id, "batch-prov-1")
			self.assertEqual(result.provenance.counts["accepted_count"], 1)
			self.assertIn("rule_ready_count", result.provenance.validation_summary)
			self.assertTrue(result.provenance.storage_path)
			stored = json.loads(Path(result.provenance.storage_path).read_text(encoding="utf-8"))
			self.assertEqual(stored["batch_id"], "batch-prov-1")

	def test_ingest_provenance_is_immutable(self) -> None:
		payload = {
			"batch_id": "batch-prov-2",
			"source": "ehr-a",
			"records": [{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}, "subject": {"reference": "Patient/pat-1"}}],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			result = ingest_batch(payload, artifact_dir=temp_dir)

			with self.assertRaises(Exception):
				result.provenance.batch_id = "mutated"  # type: ignore[misc]


if __name__ == "__main__":
	unittest.main()
