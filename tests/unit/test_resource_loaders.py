from __future__ import annotations

import unittest

from module_1_data.pipeline import ingest_batch


class ResourceLoaderTests(unittest.TestCase):
    def test_ingest_batch_all_supported_families_loaded(self) -> None:
        payload = {
            "batch_id": "batch-full",
            "source": "ehr-a",
            "records": [
                {"id": "cond-1", "resourceType": "Condition"},
                {"id": "med-1", "resourceType": "MedicationRequest"},
                {"id": "proc-1", "resourceType": "Procedure"},
                {"id": "enc-1", "resourceType": "Encounter"},
                {"id": "obs-1", "resourceType": "Observation"},
                {"id": "care-1", "resourceType": "CarePlan"},
            ],
        }

        result = ingest_batch(payload)

        families = {resource.family for resource in result.staged_resources}
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.metadata["loader_success_count"], 6)
        self.assertEqual(families, {"Condition", "Medication", "Procedure", "Encounter", "Observation", "CarePlan"})

    def test_ingest_batch_partial_family_presence_supported(self) -> None:
        payload = {
            "batch_id": "batch-partial",
            "source": "ehr-a",
            "records": [
                {"id": "cond-1", "resourceType": "Condition"},
                {"id": "obs-1", "resourceType": "Observation"},
            ],
        }

        result = ingest_batch(payload)

        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.metadata["loader_success_count"], 2)
        self.assertEqual(result.metadata["loader_failure_count"], 0)

    def test_ingest_batch_loader_failure_count_recorded(self) -> None:
        payload = {
            "batch_id": "batch-failure",
            "source": "ehr-a",
            "records": [
                {"id": "cond-1", "resourceType": "Condition"},
                {"resourceType": "Observation"},
            ],
        }

        result = ingest_batch(payload)

        self.assertEqual(result.status, "partial-ingest")
        self.assertEqual(result.metadata["accepted_count"], 1)
        self.assertEqual(result.metadata["quarantined_count"], 1)
        self.assertEqual(result.metadata["loader_success_count"], 1)
        self.assertEqual(result.metadata["loader_failure_count"], 0)
        self.assertTrue(result.validation_errors)


if __name__ == "__main__":
    unittest.main()
