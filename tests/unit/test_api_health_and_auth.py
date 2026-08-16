from __future__ import annotations

import unittest

from tests.unit.api_test_base import ApiTestCase


class HealthEndpointTests(ApiTestCase):
	def test_health_without_credentials_returns_ok(self) -> None:
		response = self.client.get("/api/v1/health")

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(body["status"], "ok")
		self.assertTrue(body["database_reachable"])

	def test_health_with_stub_engine_reports_placeholder(self) -> None:
		body = self.client.get("/api/v1/health").json()

		self.assertEqual(body["audit_engine"], "StubAuditEngine")
		self.assertTrue(body["audit_engine_is_placeholder"])

	def test_health_always_carries_audit_only_notice(self) -> None:
		body = self.client.get("/api/v1/health").json()

		self.assertIn("does not diagnose", body["audit_only_notice"])


class PrincipalResolutionTests(ApiTestCase):
	def test_session_me_without_headers_returns_401(self) -> None:
		response = self.client.get("/api/v1/session/me")

		self.assertEqual(response.status_code, 401)
		self.assertEqual(response.json()["error"], "unauthenticated")

	def test_session_me_without_role_header_returns_401(self) -> None:
		response = self.client.get("/api/v1/session/me", headers={"X-User-Id": "user-1"})

		self.assertEqual(response.status_code, 401)
		self.assertEqual(response.json()["context"]["header"], "X-User-Role")

	def test_session_me_with_unknown_role_returns_403(self) -> None:
		response = self.client.get("/api/v1/session/me", headers=self.headers(role="wizard"))

		self.assertEqual(response.status_code, 403)
		self.assertEqual(response.json()["error"], "forbidden")

	def test_session_me_with_known_role_returns_principal(self) -> None:
		response = self.client.get("/api/v1/session/me", headers=self.headers(role="compliance"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"user_id": "user-1", "role": "compliance"})

	def test_session_me_normalises_role_casing(self) -> None:
		response = self.client.get(
			"/api/v1/session/me",
			headers={"X-User-Id": "user-1", "X-User-Role": "  STEWARD "},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["role"], "steward")


if __name__ == "__main__":
	unittest.main()
