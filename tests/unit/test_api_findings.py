from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List

from module_4_api_ui.backend.audit_engine.stub_engine import STUB_RULE_PACK_VERSION
from module_4_api_ui.backend.constants import RULE_PACK_PUBLISHED
from shared.database.models import RulePackRow
from tests.unit.api_test_base import ApiTestCase


def _batch_payload(batch_id: str = "find-batch") -> Dict[str, Any]:
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


class FindingTestCase(ApiTestCase):
	def setUp(self) -> None:
		super().setUp()
		with self.session_factory() as session:
			session.add(
				RulePackRow(
					rule_pack_id="stub-rule-pack",
					version=STUB_RULE_PACK_VERSION,
					status=RULE_PACK_PUBLISHED,
					published_at=datetime.now(timezone.utc),
					metadata_json={"stale_after_days": 365, "rules": []},
				)
			)
			session.commit()

		self.batch_id = self.client.post(
			"/api/v1/batches", json=_batch_payload(), headers=self.headers()
		).json()["batch"]["id"]
		self.run_id = self.client.post(
			"/api/v1/audit-runs", json={"batch_id": self.batch_id}, headers=self.headers()
		).json()["id"]

	def findings(self, **params: Any) -> List[Dict[str, Any]]:
		return self.client.get("/api/v1/findings", params=params, headers=self.headers()).json()[
			"items"
		]

	def first_finding_id(self) -> int:
		return self.findings()[0]["id"]


class FindingQueueTests(FindingTestCase):
	def test_queue_is_ordered_by_priority_then_severity(self) -> None:
		items = self.findings()

		priorities = [item["priority"] for item in items]
		self.assertEqual(priorities, sorted(priorities))

	def test_queue_filters_by_severity(self) -> None:
		items = self.findings(severity="critical")

		self.assertTrue(items)
		self.assertTrue(all(item["severity"] == "critical" for item in items))

	def test_queue_filters_by_finding_type(self) -> None:
		items = self.findings(finding_type="missing_relationship")

		self.assertTrue(all(item["finding_type"] == "missing_relationship" for item in items))

	def test_queue_filters_by_batch(self) -> None:
		body = self.client.get(
			"/api/v1/findings", params={"batch_id": self.batch_id}, headers=self.headers()
		).json()

		self.assertGreater(body["total"], 0)

	def test_queue_search_matches_summary_text(self) -> None:
		items = self.findings(search="CarePlan")

		self.assertTrue(items)

	def test_stats_endpoint_reports_totals_by_dimension(self) -> None:
		stats = self.client.get("/api/v1/findings/stats", headers=self.headers()).json()

		self.assertGreater(stats["total"], 0)
		self.assertEqual(stats["open_total"], stats["total"])
		self.assertIn("critical", stats["by_severity"])


class FindingDetailTests(FindingTestCase):
	def test_detail_exposes_the_full_transparency_payload(self) -> None:
		detail = self.client.get(
			f"/api/v1/findings/{self.first_finding_id()}", headers=self.headers()
		).json()

		transparency = detail["transparency"]
		for field in (
			"rule_id",
			"rule_pack_version",
			"records_evaluated",
			"evidence_refs",
			"detected_at",
			"audit_outcome",
		):
			self.assertIn(field, transparency)
		self.assertTrue(transparency["records_evaluated"])
		self.assertTrue(transparency["evidence_refs"])

	def test_transparency_is_incomplete_without_an_ai_explanation(self) -> None:
		"""FR-006 counts AI rationale and confidence context as required fields."""
		detail = self.client.get(
			f"/api/v1/findings/{self.first_finding_id()}", headers=self.headers()
		).json()

		self.assertFalse(detail["transparency"]["complete"])
		self.assertIn("ai_rationale", detail["transparency"]["missing_fields"])
		self.assertIn("ai_confidence_context", detail["transparency"]["missing_fields"])

	def test_detail_carries_the_audit_only_notice(self) -> None:
		detail = self.client.get(
			f"/api/v1/findings/{self.first_finding_id()}", headers=self.headers()
		).json()

		self.assertIn("does not diagnose", detail["audit_only_notice"])

	def test_detail_lists_allowed_transitions_for_the_caller(self) -> None:
		finding_id = self.first_finding_id()

		steward = self.client.get(
			f"/api/v1/findings/{finding_id}", headers=self.headers(role="steward")
		).json()

		self.assertIn("under_review", steward["allowed_transitions"])
		self.assertNotIn("closed", steward["allowed_transitions"])

	def test_evidence_endpoint_resolves_linked_resources(self) -> None:
		evidence = self.client.get(
			f"/api/v1/findings/{self.first_finding_id()}/evidence", headers=self.headers()
		).json()

		self.assertTrue(evidence)
		self.assertIsNotNone(evidence[0]["record_external_id"])
		self.assertIsNotNone(evidence[0]["resource_type"])

	def test_unknown_finding_returns_404(self) -> None:
		response = self.client.get("/api/v1/findings/9999", headers=self.headers())

		self.assertEqual(response.status_code, 404)


class TriageTests(FindingTestCase):
	def test_accept_is_blocked_while_transparency_is_incomplete(self) -> None:
		"""UC-002 ext 2a: incomplete transparency makes a finding non-actionable."""
		response = self.client.post(
			f"/api/v1/findings/{self.first_finding_id()}/triage",
			json={"disposition": "accept"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 409)
		body = response.json()
		self.assertEqual(body["error"], "transparency_incomplete")
		self.assertIn("ai_rationale", body["context"]["missing_fields"])

	def test_escalate_from_new_writes_two_history_rows(self) -> None:
		finding_id = self.first_finding_id()

		response = self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "escalate", "notes": "needs informatics review"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 200, response.text)
		self.assertEqual(response.json()["status"], "escalated")

		history = self.client.get(
			f"/api/v1/findings/{finding_id}/history", headers=self.headers()
		).json()
		self.assertEqual([row["to_status"] for row in history], ["new", "under_review", "escalated"])

	def test_escalation_records_the_acting_user(self) -> None:
		finding_id = self.first_finding_id()
		self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "escalate"},
			headers=self.headers(user_id="steward-42"),
		)

		history = self.client.get(
			f"/api/v1/findings/{finding_id}/history", headers=self.headers()
		).json()

		self.assertEqual(history[-1]["changed_by"], "steward-42")

	def test_escalation_does_not_alter_the_deterministic_record(self) -> None:
		"""UC-002 ext 3a: a dispute must not change what the engine established."""
		finding_id = self.first_finding_id()
		before = self.client.get(f"/api/v1/findings/{finding_id}", headers=self.headers()).json()

		self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "dispute"},
			headers=self.headers(),
		)
		after = self.client.get(f"/api/v1/findings/{finding_id}", headers=self.headers()).json()

		for field in ("rule_id", "severity", "priority", "finding_type", "summary", "audit_outcome"):
			self.assertEqual(before[field], after[field], field)

	def test_defer_then_reopen_is_allowed(self) -> None:
		finding_id = self.first_finding_id()
		self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "defer"},
			headers=self.headers(),
		)

		response = self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "under_review"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["status"], "under_review")

	def test_illegal_transition_returns_409_with_allowed_targets(self) -> None:
		response = self.client.post(
			f"/api/v1/findings/{self.first_finding_id()}/status",
			json={"to_status": "closed"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 409)
		body = response.json()
		self.assertEqual(body["error"], "illegal_transition")
		self.assertIn("allowed", body["context"])

	def test_remediation_without_approved_resolution_is_refused(self) -> None:
		"""FR-009: no downstream state change on AI output alone."""
		finding_id = self.first_finding_id()
		self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "under_review"},
			headers=self.headers(),
		)

		response = self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "in_remediation"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 409)

	def test_compliance_role_cannot_triage(self) -> None:
		response = self.client.post(
			f"/api/v1/findings/{self.first_finding_id()}/triage",
			json={"disposition": "escalate"},
			headers=self.headers(role="compliance"),
		)

		self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
	unittest.main()
