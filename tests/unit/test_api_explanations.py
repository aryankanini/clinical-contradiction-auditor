from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from module_4_api_ui.backend.audit_engine.stub_engine import STUB_RULE_PACK_VERSION, StubAuditEngine
from module_4_api_ui.backend.constants import RULE_PACK_PUBLISHED
from module_4_api_ui.backend.main import create_app
from shared.database.models import FindingRow, RulePackRow
from shared.models.ai_reasoning_result import (
	AIReasoningResult,
	EvidenceSynthesis,
	ResolutionDraft,
)
from tests.unit.api_test_base import FIXED_NOW, ApiTestCase


class FakeOrchestrator:
	"""Stands in for module 3 without touching Bedrock.

	``AIReasoningOrchestrator`` takes its provider by constructor injection, so a fake at
	this level needs no mocking library.
	"""

	def __init__(
		self,
		confidence_context: str = "Moderate confidence: both records were fully normalized.",
		error: Exception | None = None,
	) -> None:
		self.confidence_context = confidence_context
		self.error = error
		self.calls: List[Dict[str, Any]] = []

	async def reason(
		self,
		finding_id: str,
		rule_id: str,
		finding_type: str,
		summary: str,
		severity: str,
		evidence_records: List[Dict[str, Any]],
	) -> AIReasoningResult:
		self.calls.append({"finding_id": finding_id, "rule_id": rule_id})
		if self.error is not None:
			raise self.error

		return AIReasoningResult(
			finding_id=finding_id,
			rule_id=rule_id,
			contradiction_explanation="The care plan remains active while the medication is stopped.",
			confidence_context=self.confidence_context,
			evidence=EvidenceSynthesis(
				record_ids=[r.get("record_id", "") for r in evidence_records],
				resource_types=["CarePlan", "MedicationRequest"],
				narrative="Two records disagree on treatment state.",
			),
			resolution_draft=ResolutionDraft(
				suggested_action="Review the care plan against the medication record.",
				rationale="The linked medication request is no longer active.",
			),
			model_name="fake-model",
			prompt_version="v1.0",
		)


def _batch_payload() -> Dict[str, Any]:
	return {
		"batch_id": "ai-batch",
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


class ExplanationTestCase(ApiTestCase):
	orchestrator: FakeOrchestrator

	def setUp(self) -> None:
		super().setUp()
		self._rebuild_app(FakeOrchestrator())

	def _rebuild_app(self, orchestrator: FakeOrchestrator) -> None:
		self.client.__exit__(None, None, None)
		self.orchestrator = orchestrator
		self.app = create_app(
			config=self.config,
			session_factory=self.session_factory,
			audit_engine=StubAuditEngine(as_of=FIXED_NOW),
			ai_orchestrator=orchestrator,
		)
		self.client = TestClient(self.app)
		self.client.__enter__()

		with self.session_factory() as session:
			if session.query(RulePackRow).count() == 0:
				session.add(
					RulePackRow(
						version=STUB_RULE_PACK_VERSION,
						status=RULE_PACK_PUBLISHED,
						published_at=datetime.now(timezone.utc),
						metadata_json={"stale_after_days": 365, "rules": []},
					)
				)
				session.commit()

		if not getattr(self, "finding_id", None):
			batch_id = self.client.post(
				"/api/v1/batches", json=_batch_payload(), headers=self.headers()
			).json()["batch"]["id"]
			self.client.post(
				"/api/v1/audit-runs", json={"batch_id": batch_id}, headers=self.headers()
			)
			items = self.client.get(
				"/api/v1/findings",
				params={"rule_id": "CONTRA-CAREPLAN-MEDREQ-STATUS"},
				headers=self.headers(),
			).json()["items"]
			self.finding_id = items[0]["id"]


class ExplanationGenerationTests(ExplanationTestCase):
	def test_generate_persists_an_explanation(self) -> None:
		response = self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation",
			json={"force_refresh": False},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 202, response.text)

		stored = self.client.get(
			f"/api/v1/findings/{self.finding_id}/explanation", headers=self.headers()
		).json()
		self.assertEqual(stored["model_name"], "fake-model")
		self.assertIn("care plan", stored["rationale_text"].lower())

	def test_generated_explanation_always_carries_the_disclaimer(self) -> None:
		"""FR-011: model-generated text may never ship without the audit-only notice."""
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation",
			json={},
			headers=self.headers(),
		)

		stored = self.client.get(
			f"/api/v1/findings/{self.finding_id}/explanation", headers=self.headers()
		).json()

		self.assertIn("Non-diagnostic", stored["disclaimer"])
		self.assertTrue(stored["resolution_draft"]["requires_human_approval"])

	def test_generating_an_explanation_never_changes_the_finding(self) -> None:
		"""FR-007: AI explains findings; it never alters their status."""
		before = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()
		history_before = self.client.get(
			f"/api/v1/findings/{self.finding_id}/history", headers=self.headers()
		).json()

		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		after = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()
		history_after = self.client.get(
			f"/api/v1/findings/{self.finding_id}/history", headers=self.headers()
		).json()

		self.assertEqual(before["status"], after["status"])
		self.assertEqual(before["severity"], after["severity"])
		self.assertEqual(before["audit_outcome"], after["audit_outcome"])
		self.assertEqual(len(history_before), len(history_after))

	def test_second_request_returns_the_cached_explanation(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		response = self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation",
			json={"force_refresh": False},
			headers=self.headers(),
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(self.orchestrator.calls), 1)

	def test_explanation_completes_the_transparency_payload(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		detail = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()

		self.assertTrue(detail["transparency"]["complete"], detail["transparency"]["missing_fields"])
		self.assertTrue(detail["transparency"]["ai_rationale_present"])

	def test_reading_an_explanation_that_was_never_generated_returns_204(self) -> None:
		items = self.client.get("/api/v1/findings", headers=self.headers()).json()["items"]
		other = next(item["id"] for item in items if item["id"] != self.finding_id)

		response = self.client.get(
			f"/api/v1/findings/{other}/explanation", headers=self.headers()
		)

		self.assertEqual(response.status_code, 204)

	def test_generate_for_unknown_finding_returns_404(self) -> None:
		response = self.client.post(
			"/api/v1/findings/9999/explanation", json={}, headers=self.headers()
		)

		self.assertEqual(response.status_code, 404)


class ExplanationDegradationTests(ExplanationTestCase):
	def test_empty_confidence_context_marks_the_draft_low_confidence(self) -> None:
		"""Module 3's marker-splitting can yield an empty confidence context."""
		self._rebuild_app(FakeOrchestrator(confidence_context=""))

		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)
		stored = self.client.get(
			f"/api/v1/findings/{self.finding_id}/explanation", headers=self.headers()
		).json()

		self.assertTrue(stored["low_confidence"])
		self.assertTrue(stored["resolution_draft"]["low_confidence"])

	def test_missing_confidence_context_keeps_transparency_incomplete(self) -> None:
		self._rebuild_app(FakeOrchestrator(confidence_context=""))

		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)
		detail = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()

		self.assertFalse(detail["transparency"]["complete"])
		self.assertIn("ai_confidence_context", detail["transparency"]["missing_fields"])

	def test_provider_failure_leaves_the_finding_usable(self) -> None:
		"""A Bedrock outage must not break evidence review."""
		self._rebuild_app(FakeOrchestrator(error=RuntimeError("bedrock throttled")))

		response = self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)
		self.assertEqual(response.status_code, 202)

		job = self.client.get(
			f"/api/v1/findings/{self.finding_id}/explanation", headers=self.headers()
		).json()
		self.assertEqual(job["state"], "failed")
		self.assertIn("bedrock throttled", job["error"])

		detail = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		)
		self.assertEqual(detail.status_code, 200)
		self.assertTrue(detail.json()["evidence"])


if __name__ == "__main__":
	unittest.main()
