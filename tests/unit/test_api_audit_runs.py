from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any, Dict

from module_4_api_ui.backend.audit_engine.stub_engine import STUB_RULE_PACK_VERSION
from module_4_api_ui.backend.constants import RULE_PACK_PUBLISHED
from shared.database.models import RulePackRow
from tests.unit.api_test_base import ApiTestCase


def _batch_payload(batch_id: str = "run-batch-1") -> Dict[str, Any]:
	return {
		"batch_id": batch_id,
		"source": "ehr-test",
		"records": [
			{
				"resourceType": "Encounter",
				"id": "enc-1",
				"status": "finished",
				"period": {"start": "2026-06-01T00:00:00Z"},
				"subject": {"reference": "Patient/p-1"},
			},
			{
				"resourceType": "MedicationRequest",
				"id": "med-1",
				"status": "stopped",
				"authoredOn": "2026-06-02T00:00:00Z",
				"subject": {"reference": "Patient/p-1"},
				"encounter": {"reference": "Encounter/enc-1"},
			},
			{
				"resourceType": "CarePlan",
				"id": "cp-1",
				"status": "active",
				"created": "2026-06-03T00:00:00Z",
				"period": {"start": "2026-06-03T00:00:00Z"},
				"subject": {"reference": "Patient/p-1"},
				"encounter": {"reference": "Encounter/enc-1"},
				"basedOn": [{"reference": "MedicationRequest/med-1"}],
			},
		],
	}


class AuditRunTestCase(ApiTestCase):
	def setUp(self) -> None:
		super().setUp()
		with self.session_factory() as session:
			session.add(
				RulePackRow(
					rule_pack_id="stub-pack-001",
					version=STUB_RULE_PACK_VERSION,
					status=RULE_PACK_PUBLISHED,
					published_at=datetime.now(timezone.utc),
					metadata_json={"stale_after_days": 365, "placeholder": True, "rules": []},
				)
			)
			session.commit()

		self.batch_id = self.client.post(
			"/api/v1/batches", json=_batch_payload(), headers=self.headers()
		).json()["batch"]["id"]


class AuditRunExecutionTests(AuditRunTestCase):
	def test_create_run_returns_202_and_completes_in_background(self) -> None:
		"""TestClient drives BackgroundTasks to completion within the request."""
		response = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		)

		self.assertEqual(response.status_code, 202, response.text)
		run_id = response.json()["id"]

		detail = self.client.get(f"/api/v1/audit-runs/{run_id}", headers=self.headers()).json()
		self.assertEqual(detail["status"], "completed")
		self.assertGreater(detail["finding_count"], 0)

	def test_completed_run_detects_the_careplan_medication_contradiction(self) -> None:
		run_id = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		).json()["id"]

		findings = self.client.get(
			"/api/v1/findings", params={"audit_run_id": run_id}, headers=self.headers()
		).json()["items"]

		rule_ids = {item["rule_id"] for item in findings}
		self.assertIn("CONTRA-CAREPLAN-MEDREQ-STATUS", rule_ids)

	def test_run_detail_reports_severity_and_outcome_histograms(self) -> None:
		run_id = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		).json()["id"]

		detail = self.client.get(f"/api/v1/audit-runs/{run_id}", headers=self.headers()).json()

		self.assertTrue(detail["severity_counts"])
		self.assertTrue(detail["outcome_counts"])
		self.assertEqual(sum(detail["severity_counts"].values()), detail["finding_count"])

	def test_every_finding_gets_a_genesis_history_row(self) -> None:
		run_id = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		).json()["id"]
		finding_id = self.client.get(
			"/api/v1/findings", params={"audit_run_id": run_id}, headers=self.headers()
		).json()["items"][0]["id"]

		history = self.client.get(
			f"/api/v1/findings/{finding_id}/history", headers=self.headers()
		).json()

		self.assertEqual(len(history), 1)
		self.assertIsNone(history[0]["from_status"])
		self.assertEqual(history[0]["to_status"], "new")
		self.assertEqual(history[0]["changed_by"], "system")

	def test_run_records_the_rule_pack_version_used(self) -> None:
		run_id = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		).json()["id"]

		detail = self.client.get(f"/api/v1/audit-runs/{run_id}", headers=self.headers()).json()

		self.assertEqual(detail["rule_pack_version"], STUB_RULE_PACK_VERSION)


class AuditRunGuardTests(AuditRunTestCase):
	def test_run_for_unknown_batch_returns_404(self) -> None:
		response = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": 9999}, headers=self.headers()
		)

		self.assertEqual(response.status_code, 404)

	def test_run_with_unknown_rule_pack_version_returns_404(self) -> None:
		response = self.client.post(
			"/api/v1/audit-runs",
			json={"batch_id": self.batch_id, "rule_pack_version": "nope-1.0"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 404)

	def test_compliance_role_cannot_trigger_a_run(self) -> None:
		response = self.client.post(
			"/api/v1/audit-runs",
			json={"batch_id": self.batch_id},
			headers=self.headers(role="compliance"),
		)

		self.assertEqual(response.status_code, 403)

	def test_unknown_run_returns_404(self) -> None:
		response = self.client.get("/api/v1/audit-runs/9999", headers=self.headers())

		self.assertEqual(response.status_code, 404)

	def test_list_runs_filters_by_batch(self) -> None:
		self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		)

		body = self.client.get(
			"/api/v1/audit-runs", params={"batch_id": self.batch_id}, headers=self.headers()
		).json()

		self.assertEqual(body["total"], 1)


class MissingRulePackTests(ApiTestCase):
	def test_run_without_a_published_rule_pack_returns_409(self) -> None:
		"""UC-001 ext 3a: a run that cannot be governed is refused, not run blind."""
		batch_id = self.client.post(
			"/api/v1/batches", json=_batch_payload("no-pack"), headers=self.headers()
		).json()["batch"]["id"]

		response = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": batch_id}, headers=self.headers()
		)

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.json()["error"], "no_published_rule_pack")


if __name__ == "__main__":
	unittest.main()
