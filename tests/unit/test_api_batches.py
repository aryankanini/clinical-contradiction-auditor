from __future__ import annotations

import io
import json
import unittest
from typing import Any, Dict

from tests.unit.api_test_base import ApiTestCase


def _record(record_id: str, resource_type: str = "Condition") -> Dict[str, Any]:
	return {
		"resourceType": resource_type,
		"id": record_id,
		"clinicalStatus": {"coding": [{"code": "active"}]},
		"recordedDate": "2026-08-01T00:00:00Z",
		"encounter": {"reference": "Encounter/enc-1"},
		"subject": {"reference": "Patient/pat-1"},
	}


def _payload(batch_id: str = "batch-api-1", records: list | None = None) -> Dict[str, Any]:
	return {
		"batch_id": batch_id,
		"source": "ehr-test",
		"records": records if records is not None else [_record("cond-1")],
	}


class BatchIngestTests(ApiTestCase):
	def test_ingest_valid_batch_returns_201_and_persists_rows(self) -> None:
		response = self.client.post(
			"/api/v1/batches", json=_payload(), headers=self.headers()
		)

		self.assertEqual(response.status_code, 201, response.text)
		body = response.json()
		self.assertEqual(body["ingest_status"], "accepted")
		self.assertEqual(body["batch"]["batch_external_id"], "batch-api-1")
		self.assertEqual(body["batch"]["accepted_count"], 1)
		self.assertGreaterEqual(body["batch"]["resource_type_counts"].get("Condition", 0), 1)

	def test_ingest_mixed_batch_returns_207_with_quarantine_detail(self) -> None:
		records = [_record("cond-1"), {"resourceType": "Unsupported", "id": "x-1"}]

		response = self.client.post(
			"/api/v1/batches", json=_payload(records=records), headers=self.headers()
		)

		self.assertEqual(response.status_code, 207, response.text)
		body = response.json()
		self.assertEqual(body["ingest_status"], "partial-ingest")
		self.assertEqual(len(body["quarantined_records"]), 1)
		self.assertTrue(body["validation_errors"])

	def test_ingest_batch_with_only_unsupported_records_returns_422(self) -> None:
		records = [{"resourceType": "Unsupported", "id": "x-1"}]

		response = self.client.post(
			"/api/v1/batches", json=_payload(records=records), headers=self.headers()
		)

		self.assertEqual(response.status_code, 422)
		self.assertEqual(response.json()["error"], "validation_error")

	def test_ingest_with_empty_records_fails_request_validation(self) -> None:
		response = self.client.post(
			"/api/v1/batches", json=_payload(records=[]), headers=self.headers()
		)

		self.assertEqual(response.status_code, 422)
		self.assertEqual(response.json()["error"], "request_validation_error")

	def test_ingest_records_provenance_and_replay_artifact_ids(self) -> None:
		body = self.client.post(
			"/api/v1/batches", json=_payload(), headers=self.headers()
		).json()

		self.assertEqual(body["provenance_id"], "prov-batch-api-1")
		self.assertEqual(body["replay_artifact_id"], "replay-batch-api-1")
		self.assertIsNotNone(body["batch"]["replay_artifact_path"])

	def test_ingest_as_compliance_role_is_forbidden(self) -> None:
		response = self.client.post(
			"/api/v1/batches", json=_payload(), headers=self.headers(role="compliance")
		)

		self.assertEqual(response.status_code, 403)

	def test_ingest_without_credentials_is_unauthenticated(self) -> None:
		response = self.client.post("/api/v1/batches", json=_payload())

		self.assertEqual(response.status_code, 401)


class BatchUploadTests(ApiTestCase):
	def test_upload_json_file_ingests_batch(self) -> None:
		buffer = io.BytesIO(json.dumps(_payload("batch-upload-1")).encode("utf-8"))

		response = self.client.post(
			"/api/v1/batches/upload",
			files={"file": ("batch.json", buffer, "application/json")},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 201, response.text)
		self.assertEqual(response.json()["batch"]["batch_external_id"], "batch-upload-1")

	def test_upload_invalid_json_returns_422(self) -> None:
		buffer = io.BytesIO(b"{not json")

		response = self.client.post(
			"/api/v1/batches/upload",
			files={"file": ("batch.json", buffer, "application/json")},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 422)
		self.assertEqual(response.json()["error"], "validation_error")


class BatchReadTests(ApiTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.client.post("/api/v1/batches", json=_payload("batch-a"), headers=self.headers())
		self.client.post("/api/v1/batches", json=_payload("batch-b"), headers=self.headers())

	def test_list_batches_returns_paginated_envelope(self) -> None:
		response = self.client.get("/api/v1/batches", headers=self.headers())

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(body["total"], 2)
		self.assertEqual(body["page"], 1)
		self.assertEqual(body["total_pages"], 1)
		self.assertEqual(len(body["items"]), 2)

	def test_list_batches_respects_page_size(self) -> None:
		body = self.client.get(
			"/api/v1/batches", params={"page_size": 1}, headers=self.headers()
		).json()

		self.assertEqual(len(body["items"]), 1)
		self.assertEqual(body["total_pages"], 2)

	def test_list_batches_filters_by_source(self) -> None:
		body = self.client.get(
			"/api/v1/batches", params={"source": "nope"}, headers=self.headers()
		).json()

		self.assertEqual(body["total"], 0)

	def test_read_unknown_batch_returns_404(self) -> None:
		response = self.client.get("/api/v1/batches/9999", headers=self.headers())

		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.json()["error"], "not_found")

	def test_batch_resources_expose_validation_state(self) -> None:
		batch_id = self.client.get("/api/v1/batches", headers=self.headers()).json()["items"][0]["id"]

		response = self.client.get(
			f"/api/v1/batches/{batch_id}/resources", headers=self.headers()
		)

		self.assertEqual(response.status_code, 200)
		items = response.json()["items"]
		self.assertTrue(items)
		self.assertIn("rule_ready", items[0])
		self.assertIn("incomplete_fields", items[0])

	def test_batch_resources_filter_by_resource_type(self) -> None:
		batch_id = self.client.get("/api/v1/batches", headers=self.headers()).json()["items"][0]["id"]

		body = self.client.get(
			f"/api/v1/batches/{batch_id}/resources",
			params={"resource_type": "Observation"},
			headers=self.headers(),
		).json()

		self.assertEqual(body["total"], 0)


if __name__ == "__main__":
	unittest.main()
