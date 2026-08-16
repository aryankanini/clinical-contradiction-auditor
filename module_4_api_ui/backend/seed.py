from __future__ import annotations

"""Populate a database with demo data for the API and UI.

    python -m module_4_api_ui.backend.seed --database-url sqlite:///./dev.db --reset

Batches are ingested through module 1's real pipeline rather than being fabricated
directly as rows. That matters for two reasons: the normalized/validation rows match
exactly what production ingestion produces, and the replay artifacts land on disk so
UC-005 reproducibility has something genuine to verify against.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from module_1_data.pipeline import ingest_batch
from module_4_api_ui.backend.audit_engine.stub_engine import (
	STUB_RULE_PACK_VERSION,
	StubAuditEngine,
)
from module_4_api_ui.backend.constants import (
	RULE_PACK_PUBLISHED,
	RUN_COMPLETED,
	RUN_RUNNING,
)
from module_4_api_ui.backend.repositories import audit_run_repository, batch_repository
from shared.database.base import Base
from shared.database.config import DatabaseConfig
from shared.database.models import ResolutionQueueRow, RulePackRow
from shared.database.session import (
	create_all_tables,
	create_engine_from_config,
	create_session_factory_for_engine,
)


NOW = datetime.now(timezone.utc)


QUEUE_DEFINITIONS = [
	{
		"name": "data-stewardship",
		"owner_type": "steward",
		"config_json": {
			"routing": {"finding_type": ["contradiction", "stale_state"]},
			"sla_hours": 24,
			"is_default_escalation": False,
		},
	},
	{
		"name": "clinical-informatics",
		"owner_type": "analyst",
		"config_json": {
			"routing": {"finding_type": ["timeline_violation"]},
			"sla_hours": 48,
			"is_default_escalation": False,
		},
	},
	{
		"name": "operations",
		"owner_type": "operations",
		"config_json": {
			"routing": {"finding_type": ["missing_relationship"]},
			"sla_hours": 72,
			"is_default_escalation": False,
		},
	},
	{
		"name": "governance-escalation",
		"owner_type": "compliance",
		"config_json": {"routing": {}, "sla_hours": 12, "is_default_escalation": True},
	},
]


RULE_DESCRIPTORS = [
	{"rule_id": "CONTRA-CAREPLAN-MEDREQ-STATUS", "type": "contradiction", "requirement": "FR-003"},
	{"rule_id": "CONTRA-CONDITION-ENCOUNTER-STATE", "type": "contradiction", "requirement": "FR-003"},
	{"rule_id": "STALE-STATUS-OPEN", "type": "stale_state", "requirement": "FR-004"},
	{"rule_id": "TIMELINE-EVENT-PRECEDES-ENCOUNTER", "type": "timeline_violation", "requirement": "FR-004"},
	{"rule_id": "TIMELINE-FUTURE-EVENT", "type": "timeline_violation", "requirement": "FR-004"},
	{"rule_id": "REL-{TYPE}-{FIELD}", "type": "missing_relationship", "requirement": "FR-005"},
]


def _iso(delta_days: int) -> str:
	return (NOW + timedelta(days=delta_days)).isoformat()


def contradiction_batch() -> Dict[str, Any]:
	"""An active care plan still pointing at a stopped medication (the BRD's example)."""
	return {
		"batch_id": "demo-contradiction",
		"source": "ehr-alpha",
		"records": [
			{
				"resourceType": "Encounter",
				"id": "enc-100",
				"status": "finished",
				"period": {"start": _iso(-30)},
				"subject": {"reference": "Patient/pat-1"},
			},
			{
				"resourceType": "MedicationRequest",
				"id": "med-100",
				"status": "stopped",
				"authoredOn": _iso(-28),
				"subject": {"reference": "Patient/pat-1"},
				"encounter": {"reference": "Encounter/enc-100"},
			},
			{
				"resourceType": "CarePlan",
				"id": "cp-100",
				"status": "active",
				"period": {"start": _iso(-25)},
				"created": _iso(-25),
				"subject": {"reference": "Patient/pat-1"},
				"encounter": {"reference": "Encounter/enc-100"},
				"basedOn": [{"reference": "MedicationRequest/med-100"}],
			},
			{
				"resourceType": "Condition",
				"id": "cond-100",
				"clinicalStatus": {"coding": [{"code": "active"}]},
				"recordedDate": _iso(-27),
				"subject": {"reference": "Patient/pat-1"},
				"encounter": {"reference": "Encounter/enc-999"},
			},
		],
	}


def stale_and_timeline_batch() -> Dict[str, Any]:
	"""A long-open condition, a future observation, and an out-of-order event."""
	return {
		"batch_id": "demo-stale-timeline",
		"source": "ehr-beta",
		"records": [
			{
				"resourceType": "Encounter",
				"id": "enc-200",
				"status": "finished",
				"period": {"start": _iso(-100)},
				"subject": {"reference": "Patient/pat-2"},
			},
			{
				"resourceType": "Condition",
				"id": "cond-200",
				"clinicalStatus": {"coding": [{"code": "active"}]},
				"recordedDate": _iso(-800),
				"subject": {"reference": "Patient/pat-2"},
				"encounter": {"reference": "Encounter/enc-200"},
			},
			{
				"resourceType": "Observation",
				"id": "obs-200",
				"status": "final",
				"effectiveDateTime": _iso(-400),
				"subject": {"reference": "Patient/pat-2"},
				"encounter": {"reference": "Encounter/enc-200"},
			},
			{
				"resourceType": "Observation",
				"id": "obs-201",
				"status": "final",
				"effectiveDateTime": _iso(30),
				"subject": {"reference": "Patient/pat-2"},
				"encounter": {"reference": "Encounter/enc-200"},
			},
		],
	}


def relationship_gap_batch() -> Dict[str, Any]:
	"""Missing rule-expected links, plus a record that must be quarantined."""
	return {
		"batch_id": "demo-relationship-gaps",
		"source": "ehr-gamma",
		"records": [
			{
				"resourceType": "Condition",
				"id": "cond-300",
				"clinicalStatus": {"coding": [{"code": "resolved"}]},
				"recordedDate": _iso(-10),
				"subject": {"reference": "Patient/pat-3"},
			},
			{
				"resourceType": "Procedure",
				"id": "proc-300",
				"status": "completed",
				"performedDateTime": _iso(-9),
			},
			{
				"resourceType": "CarePlan",
				"id": "cp-300",
				"status": "draft",
				"created": _iso(-8),
			},
			{
				"resourceType": "DiagnosticReport",
				"id": "dr-300",
				"status": "final",
			},
		],
	}


DEMO_BATCHES = [contradiction_batch, stale_and_timeline_batch, relationship_gap_batch]


def seed_rule_pack(session) -> RulePackRow:
	existing = session.query(RulePackRow).filter_by(version=STUB_RULE_PACK_VERSION).one_or_none()
	if existing is not None:
		return existing

	row = RulePackRow(
		version=STUB_RULE_PACK_VERSION,
		status=RULE_PACK_PUBLISHED,
		published_at=NOW,
		metadata_json={
			"source": "module_4_stub",
			"placeholder": True,
			"owner": "module_2_audit_engine (pending)",
			"note": (
				"Placeholder rule pack shipped with the API so the UI is demoable before "
				"the deterministic engine lands. Not authoritative clinical policy."
			),
			"stale_after_days": 365,
			"rules": RULE_DESCRIPTORS,
		},
	)
	session.add(row)
	session.flush()
	return row


def seed_queues(session) -> List[ResolutionQueueRow]:
	rows: List[ResolutionQueueRow] = []
	for definition in QUEUE_DEFINITIONS:
		existing = (
			session.query(ResolutionQueueRow).filter_by(name=definition["name"]).one_or_none()
		)
		if existing is not None:
			rows.append(existing)
			continue
		row = ResolutionQueueRow(**definition)
		session.add(row)
		rows.append(row)
	session.flush()
	return rows


def run_audit(session, engine, batch_id: int, rule_pack: RulePackRow) -> int:
	run = audit_run_repository.create_run(session, batch_id, rule_pack.id)
	audit_run_repository.set_run_status(session, run, RUN_RUNNING)
	session.flush()

	records = batch_repository.load_audit_inputs(session, batch_id)
	result = engine.evaluate_batch(records, dict(rule_pack.metadata_json or {}))
	resource_ids = audit_run_repository.normalized_resource_ids(session, batch_id)
	findings = audit_run_repository.persist_findings(session, run, result.findings, resource_ids)
	audit_run_repository.set_run_status(session, run, RUN_COMPLETED, completed=True)
	session.commit()
	return len(findings)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Seed demo rule packs, queues, batches, and findings for the module 4 API."
	)
	parser.add_argument(
		"--database-url",
		default=None,
		help="SQLAlchemy database URL (defaults to DATABASE_URL from the environment)",
	)
	parser.add_argument(
		"--artifact-dir",
		default="data/processed/ingest-artifacts",
		help="Directory for provenance and replay artifacts",
	)
	parser.add_argument(
		"--reset",
		action="store_true",
		help="Drop and recreate all tables before seeding",
	)
	return parser


def main(argv: List[str] | None = None) -> int:
	args = build_parser().parse_args(argv)

	config = (
		DatabaseConfig(url=args.database_url)
		if args.database_url
		else DatabaseConfig.from_env()
	)
	engine = create_engine_from_config(config)

	try:
		if args.reset:
			Base.metadata.drop_all(bind=engine)
		create_all_tables(engine)
		session_factory = create_session_factory_for_engine(engine)

		with session_factory() as session:
			rule_pack = seed_rule_pack(session)
			queues = seed_queues(session)
			session.commit()
			rule_pack_id = rule_pack.id
			queue_count = len(queues)

		Path(args.artifact_dir).mkdir(parents=True, exist_ok=True)
		audit_engine = StubAuditEngine()
		summary: Dict[str, Any] = {
			"rule_pack_version": STUB_RULE_PACK_VERSION,
			"queues": queue_count,
			"batches": [],
		}

		for build_batch in DEMO_BATCHES:
			payload = build_batch()
			result = ingest_batch(
				payload,
				artifact_dir=args.artifact_dir,
				database_url=config.url,
			)
			database_batch_id = result.metadata.get("database_batch_id")
			if database_batch_id is None:
				summary["batches"].append(
					{"batch_id": payload["batch_id"], "status": result.status, "findings": 0}
				)
				continue

			with session_factory() as session:
				pack = session.get(RulePackRow, rule_pack_id)
				finding_count = run_audit(session, audit_engine, int(database_batch_id), pack)

			summary["batches"].append(
				{
					"batch_id": payload["batch_id"],
					"database_batch_id": int(database_batch_id),
					"status": result.status,
					"findings": finding_count,
				}
			)

		print(json.dumps(summary, indent=2))
	finally:
		engine.dispose()

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
