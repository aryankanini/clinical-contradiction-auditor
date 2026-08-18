from __future__ import annotations

import unittest
from typing import Any

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.database.base import Base
from shared.database.models import AuditTrailRow, ExecutionPlanRow, FindingHashRow, FindingRow, RulePackRow
from shared.database.session import get_migration_paths


class RuleExecutionPersistenceTests(unittest.TestCase):
	def setUp(self) -> None:
		self.engine = create_engine("sqlite+pysqlite:///:memory:")

		@event.listens_for(self.engine, "connect")
		def enable_foreign_keys(dbapi_connection: Any, _: object) -> None:
			dbapi_connection.execute("PRAGMA foreign_keys=ON")

		Base.metadata.create_all(self.engine)

	def tearDown(self) -> None:
		self.engine.dispose()

	def test_schema_creates_rule_execution_tables(self) -> None:
		table_names = set(inspect(self.engine).get_table_names())

		self.assertTrue(
			{
				"rule_packs",
				"rule_pack_rules",
				"execution_plans",
				"execution_plan_rules",
				"audit_trail",
			}.issubset(table_names)
		)

	def test_audit_trail_delete_is_rejected(self) -> None:
		with Session(self.engine) as session:
			rule_pack = RulePackRow(
				rule_pack_id="PACK-TEST-001",
				version="1.0.0",
				metadata_json={},
			)
			session.add(rule_pack)
			session.flush()
			audit_entry = AuditTrailRow(
				batch_run_id="00000000-0000-0000-0000-000000000001",
				rule_pack_version="1.0.0",
				rule_pack_id=rule_pack.id,
				cohort_size=1,
			)
			session.add(audit_entry)
			session.commit()

			session.delete(audit_entry)
			with self.assertRaisesRegex(ValueError, "append-only"):
				session.flush()

	def test_execution_plan_requires_existing_rule_pack(self) -> None:
		with Session(self.engine) as session:
			session.add(
				ExecutionPlanRow(
					batch_run_id="00000000-0000-0000-0000-000000000002",
					rule_pack_id=999,
				)
			)
			with self.assertRaises(IntegrityError):
				session.commit()

	def test_migration_path_includes_rule_execution_schema(self) -> None:
		migration_names = [path.name for path in get_migration_paths()]

		self.assertIn("001_rule_packs_and_logs.sql", migration_names)
		self.assertIn("002_findings_and_evidence.sql", migration_names)
		self.assertIn("003_timeline_artifacts.sql", migration_names)
		self.assertIn("004_audit_log_reproducibility.sql", migration_names)

	def test_schema_creates_timeline_artifact_tables(self) -> None:
		table_names = set(inspect(self.engine).get_table_names())
		self.assertTrue({"timeline_findings", "stale_states", "state_transitions"}.issubset(table_names))

	def test_finding_hash_requires_unique_finding(self) -> None:
		with Session(self.engine) as session:
			finding = FindingRow(audit_run_id=1, rule_id="RULE-001", severity="warning", priority="normal", finding_type="contradiction", status="active", summary="summary", audit_outcome="FLAGGED")
			session.add(finding)
			with self.assertRaises(IntegrityError):
				session.flush()


if __name__ == "__main__":
	unittest.main()