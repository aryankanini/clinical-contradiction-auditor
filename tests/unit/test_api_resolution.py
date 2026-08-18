from __future__ import annotations

import unittest
from typing import Any, Dict

from shared.database.models import ResolutionQueueRow
from tests.unit.test_api_explanations import ExplanationTestCase


QUEUES = [
	{
		"name": "data-stewardship",
		"owner_type": "steward",
		"config_json": {"routing": {"finding_type": ["contradiction", "stale_state"]}},
	},
	{
		"name": "clinical-informatics",
		"owner_type": "analyst",
		"config_json": {"routing": {"finding_type": ["timeline_violation"]}},
	},
	{
		"name": "governance-escalation",
		"owner_type": "compliance",
		"config_json": {"routing": {}, "is_default_escalation": True},
	},
]


class ResolutionTestCase(ExplanationTestCase):
	def setUp(self) -> None:
		super().setUp()
		with self.session_factory() as session:
			if session.query(ResolutionQueueRow).count() == 0:
				for definition in QUEUES:
					session.add(ResolutionQueueRow(**definition))
				session.commit()

	def approved_payload(self, source: str = "manual") -> Dict[str, Any]:
		return {
			"suggested_action": "Reconcile the care plan against the medication record.",
			"rationale": "The linked medication request is no longer active.",
			"source": source,
		}


class ResolutionApprovalTests(ResolutionTestCase):
	def test_manual_resolution_is_recorded_with_the_approver(self) -> None:
		response = self.client.put(
			f"/api/v1/findings/{self.finding_id}/resolution",
			json=self.approved_payload(),
			headers=self.headers(user_id="steward-7"),
		)

		self.assertEqual(response.status_code, 200, response.text)
		body = response.json()
		self.assertEqual(body["source"], "manual")
		self.assertEqual(body["approved_by"], "steward-7")
		self.assertIn("requires human review", body["audit_only_note"])

	def test_ai_sourced_resolution_without_a_draft_is_refused(self) -> None:
		"""UC-003 ext 2a: with no draft available, the steward must write it."""
		response = self.client.put(
			f"/api/v1/findings/{self.finding_id}/resolution",
			json=self.approved_payload(source="ai"),
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 422)
		self.assertEqual(response.json()["error"], "ai_draft_unavailable")

	def test_ai_sourced_resolution_is_allowed_once_a_draft_exists(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		response = self.client.put(
			f"/api/v1/findings/{self.finding_id}/resolution",
			json=self.approved_payload(source="ai"),
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 200, response.text)

	def test_analyst_cannot_approve_a_resolution(self) -> None:
		response = self.client.put(
			f"/api/v1/findings/{self.finding_id}/resolution",
			json=self.approved_payload(),
			headers=self.headers(role="analyst"),
		)

		self.assertEqual(response.status_code, 403)

	def test_draft_endpoint_returns_the_generated_action(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		draft = self.client.get(
			f"/api/v1/findings/{self.finding_id}/resolution/draft", headers=self.headers()
		).json()

		self.assertIn("suggested_action", draft)
		self.assertTrue(draft["requires_human_approval"])


class AssignmentTests(ResolutionTestCase):
	def test_auto_routing_matches_the_queue_config(self) -> None:
		response = self.client.post(
			f"/api/v1/findings/{self.finding_id}/assignment", json={}, headers=self.headers()
		)

		self.assertEqual(response.status_code, 200, response.text)
		body = response.json()
		self.assertEqual(body["queue_name"], "data-stewardship")
		self.assertTrue(body["auto_routed"])
		self.assertFalse(body["escalated"])

	def test_explicit_queue_assignment_is_honoured(self) -> None:
		queues = self.client.get("/api/v1/queues", headers=self.headers()).json()
		informatics = next(q for q in queues if q["name"] == "clinical-informatics")

		body = self.client.post(
			f"/api/v1/findings/{self.finding_id}/assignment",
			json={"queue_id": informatics["id"], "assigned_to": "analyst-3"},
			headers=self.headers(),
		).json()

		self.assertEqual(body["queue_name"], "clinical-informatics")
		self.assertEqual(body["assigned_to"], "analyst-3")
		self.assertFalse(body["auto_routed"])

	def test_unknown_queue_returns_404(self) -> None:
		response = self.client.post(
			f"/api/v1/findings/{self.finding_id}/assignment",
			json={"queue_id": 9999},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 404)

	def test_queue_worklist_lists_assigned_findings(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/assignment", json={}, headers=self.headers()
		)
		queues = self.client.get("/api/v1/queues", headers=self.headers()).json()
		stewardship = next(q for q in queues if q["name"] == "data-stewardship")

		body = self.client.get(
			f"/api/v1/queues/{stewardship['id']}/findings", headers=self.headers()
		).json()

		self.assertEqual(body["total"], 1)
		self.assertEqual(body["items"][0]["id"], self.finding_id)

	def test_queue_open_counts_reflect_assignments(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/assignment", json={}, headers=self.headers()
		)

		queues = self.client.get("/api/v1/queues", headers=self.headers()).json()
		stewardship = next(q for q in queues if q["name"] == "data-stewardship")

		self.assertEqual(stewardship["open_count"], 1)


class ClosureWorkflowTests(ResolutionTestCase):
	def test_full_accept_to_closed_walk(self) -> None:
		"""UC-003: triage -> approve -> assign -> remediate -> close, with a full trail."""
		finding_id = self.finding_id

		# An explanation is required before acceptance, since FR-006 counts AI rationale
		# among the transparency fields.
		self.client.post(
			f"/api/v1/findings/{finding_id}/explanation", json={}, headers=self.headers()
		)

		accepted = self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "accept"},
			headers=self.headers(),
		)
		self.assertEqual(accepted.status_code, 200, accepted.text)
		self.assertEqual(accepted.json()["status"], "accepted")

		self.client.put(
			f"/api/v1/findings/{finding_id}/resolution",
			json=self.approved_payload(source="ai_edited"),
			headers=self.headers(),
		)
		self.client.post(
			f"/api/v1/findings/{finding_id}/assignment", json={}, headers=self.headers()
		)

		for target in ("in_remediation", "remediated"):
			response = self.client.post(
				f"/api/v1/findings/{finding_id}/status",
				json={"to_status": target},
				headers=self.headers(),
			)
			self.assertEqual(response.status_code, 200, f"{target}: {response.text}")

		closed = self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "closed", "notes": "verified"},
			headers=self.headers(role="compliance"),
		)

		self.assertEqual(closed.status_code, 200, closed.text)
		self.assertEqual(closed.json()["status"], "closed")

		history = self.client.get(
			f"/api/v1/findings/{finding_id}/history", headers=self.headers()
		).json()
		self.assertEqual(
			[row["to_status"] for row in history],
			["new", "under_review", "accepted", "in_remediation", "remediated", "closed"],
		)

	def test_closed_finding_rejects_further_transitions(self) -> None:
		finding_id = self.finding_id
		self.client.post(
			f"/api/v1/findings/{finding_id}/explanation", json={}, headers=self.headers()
		)
		self.client.post(
			f"/api/v1/findings/{finding_id}/triage",
			json={"disposition": "accept"},
			headers=self.headers(),
		)
		self.client.put(
			f"/api/v1/findings/{finding_id}/resolution",
			json=self.approved_payload(),
			headers=self.headers(),
		)
		self.client.post(
			f"/api/v1/findings/{finding_id}/assignment", json={}, headers=self.headers()
		)
		for target in ("in_remediation", "remediated"):
			self.client.post(
				f"/api/v1/findings/{finding_id}/status",
				json={"to_status": target},
				headers=self.headers(),
			)
		self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "closed"},
			headers=self.headers(role="compliance"),
		)

		response = self.client.post(
			f"/api/v1/findings/{finding_id}/status",
			json={"to_status": "under_review"},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
	unittest.main()
