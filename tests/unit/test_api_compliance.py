from __future__ import annotations

import unittest

from module_4_api_ui.backend.repositories import batch_repository
from tests.unit.test_api_explanations import ExplanationTestCase


class ComplianceTestCase(ExplanationTestCase):
	def compliance_headers(self) -> dict:
		return self.headers(role="compliance", user_id="reviewer-1")


class SampleSelectionTests(ComplianceTestCase):
	def test_same_seed_selects_the_same_findings(self) -> None:
		"""A reviewer must be able to reproduce a colleague's sample exactly."""
		first = self.client.post(
			"/api/v1/compliance/samples",
			json={"sample_size": 2, "seed": 42},
			headers=self.compliance_headers(),
		).json()
		second = self.client.post(
			"/api/v1/compliance/samples",
			json={"sample_size": 2, "seed": 42},
			headers=self.compliance_headers(),
		).json()

		self.assertEqual(first["finding_ids"], second["finding_ids"])
		self.assertEqual(len(first["finding_ids"]), 2)

	def test_sample_size_is_capped_by_candidate_count(self) -> None:
		body = self.client.post(
			"/api/v1/compliance/samples",
			json={"sample_size": 500, "seed": 1},
			headers=self.compliance_headers(),
		).json()

		self.assertEqual(len(body["finding_ids"]), body["candidate_count"])

	def test_severity_filter_narrows_the_candidate_pool(self) -> None:
		body = self.client.post(
			"/api/v1/compliance/samples",
			json={"sample_size": 10, "seed": 1, "severity": ["critical"]},
			headers=self.compliance_headers(),
		).json()

		self.assertGreaterEqual(body["candidate_count"], 1)

	def test_non_compliance_role_cannot_sample(self) -> None:
		response = self.client.post(
			"/api/v1/compliance/samples",
			json={"sample_size": 1},
			headers=self.headers(role="steward"),
		)

		self.assertEqual(response.status_code, 403)


class ReproducibilityTests(ComplianceTestCase):
	def test_finding_with_intact_artifacts_is_reproducible(self) -> None:
		body = self.client.get(
			f"/api/v1/compliance/findings/{self.finding_id}/reproducibility",
			headers=self.compliance_headers(),
		).json()

		self.assertTrue(body["reproducible"], body["checks"])
		self.assertEqual(body["missing_artifacts"], [])
		names = {check["name"] for check in body["checks"]}
		self.assertIn("replay_artifact_readable", names)
		self.assertIn("evidence_reconstructable", names)

	def test_missing_replay_artifact_fails_reproducibility_without_erroring(self) -> None:
		"""UC-005 ext 2a: a missing artifact is a failed sample, not a 500."""
		with self.session_factory() as session:
			detail = self.client.get(
				f"/api/v1/findings/{self.finding_id}", headers=self.headers()
			).json()
			run_id = detail["audit_run_id"]
			from shared.database.models import AuditRunRow

			run = session.get(AuditRunRow, run_id)
			batch = batch_repository.get_batch(session, run.batch_id)
			batch.replay_artifact_path = None
			session.commit()

		response = self.client.get(
			f"/api/v1/compliance/findings/{self.finding_id}/reproducibility",
			headers=self.compliance_headers(),
		)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertFalse(body["reproducible"])
		self.assertIn("replay_artifact", body["missing_artifacts"])

	def test_unknown_finding_returns_404(self) -> None:
		response = self.client.get(
			"/api/v1/compliance/findings/9999/reproducibility",
			headers=self.compliance_headers(),
		)

		self.assertEqual(response.status_code, 404)


class VerificationTests(ComplianceTestCase):
	def test_verification_is_recorded_against_the_finding(self) -> None:
		response = self.client.post(
			f"/api/v1/compliance/findings/{self.finding_id}/verification",
			json={"outcome": "passed", "notes": "artifacts intact"},
			headers=self.compliance_headers(),
		)

		self.assertEqual(response.status_code, 200, response.text)
		body = response.json()
		self.assertEqual(body["outcome"], "passed")
		self.assertEqual(body["verified_by"], "reviewer-1")

	def test_verification_does_not_pollute_engine_evidence(self) -> None:
		"""Service-written evidence must not be mistaken for what the engine produced."""
		before = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()

		self.client.post(
			f"/api/v1/compliance/findings/{self.finding_id}/verification",
			json={"outcome": "passed"},
			headers=self.compliance_headers(),
		)
		after = self.client.get(
			f"/api/v1/findings/{self.finding_id}", headers=self.headers()
		).json()

		self.assertEqual(len(before["evidence"]), len(after["evidence"]))


class ExportTests(ComplianceTestCase):
	def test_export_bundle_contains_the_finding_and_its_replay_snapshots(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		response = self.client.post(
			"/api/v1/compliance/exports",
			json={"finding_ids": [self.finding_id], "include_replay_snapshots": True},
			headers=self.compliance_headers(),
		)

		self.assertEqual(response.status_code, 200, response.text)
		body = response.json()
		self.assertEqual(len(body["items"]), 1)

		item = body["items"][0]
		self.assertEqual(item["finding"]["id"], self.finding_id)
		self.assertTrue(item["replay_snapshots"])
		self.assertTrue(item["reproducibility"]["reproducible"])
		self.assertIn("does not diagnose", body["audit_only_notice"])

	def test_export_is_written_to_the_export_directory(self) -> None:
		body = self.client.post(
			"/api/v1/compliance/exports",
			json={"finding_ids": [self.finding_id]},
			headers=self.compliance_headers(),
		).json()

		self.assertIsNotNone(body["export_path"])

	def test_exported_finding_carries_its_full_transparency_payload(self) -> None:
		self.client.post(
			f"/api/v1/findings/{self.finding_id}/explanation", json={}, headers=self.headers()
		)

		body = self.client.post(
			"/api/v1/compliance/exports",
			json={"finding_ids": [self.finding_id]},
			headers=self.compliance_headers(),
		).json()

		transparency = body["items"][0]["finding"]["transparency"]
		self.assertTrue(transparency["complete"], transparency["missing_fields"])
		self.assertTrue(transparency["records_evaluated"])

	def test_export_requires_the_compliance_role(self) -> None:
		response = self.client.post(
			"/api/v1/compliance/exports",
			json={"finding_ids": [self.finding_id]},
			headers=self.headers(role="steward"),
		)

		self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
	unittest.main()
