from __future__ import annotations

"""Shared harness for module 4 API tests.

Named ``api_test_base`` rather than ``test_*`` so ``unittest discover`` does not collect
it as a test module.

Uses a temp-file SQLite database, not ``:memory:``. ``TestClient`` runs the app in a
worker thread and FastAPI dispatches sync routes to a threadpool; the pysqlite dialect
gives ``:memory:`` a ``SingletonThreadPool``, so each thread would see its own empty
database. The whole schema works on SQLite because ``shared/database/models.py``
declares ``JSON().with_variant(JSONB, "postgresql")``.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi.testclient import TestClient

from module_4_api_ui.backend.audit_engine.stub_engine import StubAuditEngine
from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.main import create_app
from shared.database.config import DatabaseConfig
from shared.database.session import (
	create_all_tables,
	create_engine_from_config,
	create_session_factory_for_engine,
)


# Fixed clock so stale/timeline rules are reproducible.
FIXED_NOW = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)


class ApiTestCase(unittest.TestCase):
	"""Boots the API against an isolated on-disk SQLite database."""

	def setUp(self) -> None:
		self._temp = tempfile.TemporaryDirectory()
		database_url = "sqlite+pysqlite:///" + self._temp.name.replace("\\", "/") + "/api-test.db"

		self.config = ApiConfig(
			database_url=database_url,
			artifact_dir=self._temp.name,
			export_dir=self._temp.name,
			auto_create_tables=True,
		)
		self.engine = create_engine_from_config(DatabaseConfig(url=database_url))
		create_all_tables(self.engine)
		self.session_factory = create_session_factory_for_engine(self.engine)

		self.app = create_app(
			config=self.config,
			session_factory=self.session_factory,
			audit_engine=StubAuditEngine(as_of=FIXED_NOW),
		)
		self.client = TestClient(self.app)
		self.client.__enter__()

	def tearDown(self) -> None:
		self.client.__exit__(None, None, None)
		# Windows will not remove the temp directory while the engine holds the file.
		self.engine.dispose()
		self._temp.cleanup()

	def headers(self, role: str = "steward", user_id: str = "user-1") -> Dict[str, str]:
		return {"X-User-Id": user_id, "X-User-Role": role}


def audit_input(
	record_id: str,
	resource_type: str,
	status: str,
	*,
	family: str | None = None,
	timestamps: Dict[str, Any] | None = None,
	references: Dict[str, Any] | None = None,
	incomplete_fields: list[str] | None = None,
	unresolved_links: list[str] | None = None,
	rule_ready: bool = True,
	status_state: str = "valid",
	normalized_resource_id: int | None = None,
) -> Dict[str, Any]:
	"""Build one audit-input record in the canonical replay-snapshot shape."""
	return {
		"record_id": record_id,
		"resource_type": resource_type,
		"family": family or resource_type,
		"status": status,
		"status_state": status_state,
		"timestamps": timestamps or {},
		"references": references or {},
		"incomplete_fields": incomplete_fields or [],
		"unresolved_links": unresolved_links or [],
		"governed_signals": [],
		"rule_ready": rule_ready,
		"normalized_resource_id": normalized_resource_id,
	}


def reference(target_id: str, state: str = "valid") -> Dict[str, Any]:
	return {"reference": target_id, "target_id": target_id, "state": state, "source_path": ""}
