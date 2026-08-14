from __future__ import annotations

import unittest

from module_1_data.ingestion.parser import validate_batch_contract


class ValidateBatchContractTests(unittest.TestCase):
    def test_validate_batch_contract_supported_payload_accepted(self) -> None:
        payload = {
            "batch_id": "batch-001",
            "source": "ehr-a",
            "records": [
                {"id": "cond-1", "resourceType": "Condition"},
                {"id": "med-1", "resourceType": "MedicationRequest"},
            ],
        }

        result = validate_batch_contract(payload)

        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.metadata["accepted_count"], 2)
        self.assertEqual(result.metadata["quarantined_count"], 0)

    def test_validate_batch_contract_malformed_envelope_rejected(self) -> None:
        payload = {"source": "ehr-a", "records": []}

        result = validate_batch_contract(payload)

        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.errors[0].reason, "batch_id must be a non-empty string")

    def test_validate_batch_contract_unsupported_resource_quarantined(self) -> None:
        payload = {
            "batch_id": "batch-002",
            "source": "ehr-a",
            "records": [{"id": "abc", "resourceType": "AllergyIntolerance"}],
        }

        result = validate_batch_contract(payload)

        self.assertEqual(result.status, "quarantined")
        self.assertEqual(result.metadata["accepted_count"], 0)
        self.assertEqual(result.metadata["quarantined_count"], 1)
        self.assertEqual(result.errors[0].reason, "unsupported resourceType")

    def test_validate_batch_contract_mixed_records_partial_ingest(self) -> None:
        payload = {
            "batch_id": "batch-003",
            "source": "ehr-a",
            "records": [
                {"id": "enc-1", "resourceType": "Encounter"},
                {"id": "bad-1", "resourceType": "AllergyIntolerance"},
            ],
        }

        result = validate_batch_contract(payload)

        self.assertEqual(result.status, "partial-ingest")
        self.assertEqual(result.metadata["accepted_count"], 1)
        self.assertEqual(result.metadata["quarantined_count"], 1)

    def test_validate_batch_contract_empty_records_rejected(self) -> None:
        payload = {"batch_id": "batch-004", "source": "ehr-a", "records": []}

        result = validate_batch_contract(payload)

        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.errors[0].reason, "records must not be empty")


if __name__ == "__main__":
    unittest.main()
