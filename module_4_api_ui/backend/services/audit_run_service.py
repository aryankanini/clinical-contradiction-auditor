from __future__ import annotations

"""Deterministic audit execution (UC-001, FR-003/FR-004/FR-005/FR-008)."""

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session, sessionmaker

from module_4_api_ui.backend.audit_engine.port import AuditEnginePort
from module_4_api_ui.backend.constants import (
	RUN_COMPLETED,
	RUN_FAILED,
	RUN_RUNNING,
)
from module_4_api_ui.backend.errors import ConflictError, NotFoundError
from module_4_api_ui.backend.repositories import (
	audit_run_repository,
	batch_repository,
	catalog_repository,
	finding_repository,
)
from module_4_api_ui.backend.schemas.catalog import AuditRunDetailOut, AuditRunOut
from module_4_api_ui.backend.services.job_registry import JobRegistry
from shared.database.models import AuditRunRow, FindingRow


logger = logging.getLogger("clinical_auditor.api.audit_run")


def _run_out(run: AuditRunRow) -> AuditRunOut:
	return AuditRunOut(
		id=run.id,
		batch_id=run.batch_id,
		batch_external_id=run.batch.batch_external_id if run.batch else None,
		rule_pack_id=run.rule_pack_id,
		rule_pack_version=run.rule_pack.version if run.rule_pack else None,
		status=run.status,
		started_at=run.started_at,
		completed_at=run.completed_at,
	)


class AuditRunService:
	"""Triggers and reports deterministic audit runs.

	Execution happens in a background task rather than inline: a run is CPU work over an
	entire batch, and the durable status already lives on ``audit_runs``, so the client
	polls instead of holding a request open.
	"""

	def __init__(
		self,
		session_factory: "sessionmaker[Session]",
		engine: AuditEnginePort,
		job_registry: JobRegistry | None = None,
	) -> None:
		self._session_factory = session_factory
		self._engine = engine
		self._jobs = job_registry

	def create_run(
		self,
		session: Session,
		batch_id: int,
		rule_pack_version: str | None,
	) -> AuditRunOut:
		batch = batch_repository.get_batch(session, batch_id)
		if batch is None:
			raise NotFoundError(f"Batch {batch_id} was not found.")

		if audit_run_repository.has_active_run(session, batch_id):
			raise ConflictError(
				"An audit run is already in progress for this batch.",
				code="run_already_active",
				context={"batch_id": batch_id},
			)

		if rule_pack_version:
			rule_pack = catalog_repository.get_rule_pack_by_version(session, rule_pack_version)
			if rule_pack is None:
				raise NotFoundError(
					f"Rule pack version '{rule_pack_version}' was not found.",
					context={"rule_pack_version": rule_pack_version},
				)
		else:
			rule_pack = catalog_repository.get_published_rule_pack(session)
			if rule_pack is None:
				# UC-001 extension 3a: without a published pack the run cannot be
				# governed, so it is refused rather than run against nothing.
				raise ConflictError(
					"No published rule pack is available; an audit run cannot be governed.",
					code="no_published_rule_pack",
				)

		run = audit_run_repository.create_run(session, batch_id, rule_pack.id)
		session.commit()
		session.refresh(run)
		return _run_out(run)

	def execute(self, run_id: int) -> None:
		"""Run the engine over a batch and persist its findings.

		Opens its own session because it executes after the request that queued it has
		already returned and closed its own.
		"""
		with self._session_factory() as session:
			run = audit_run_repository.get_run(session, run_id)
			if run is None:
				logger.error("Audit run %s vanished before execution", run_id)
				return

			audit_run_repository.set_run_status(session, run, RUN_RUNNING)
			session.commit()

			try:
				records = batch_repository.load_audit_inputs(session, run.batch_id)
				rule_pack = dict(run.rule_pack.metadata_json or {}) if run.rule_pack else {}

				result = self._engine.evaluate_batch(records, rule_pack)

				resource_ids = audit_run_repository.normalized_resource_ids(session, run.batch_id)
				audit_run_repository.persist_findings(session, run, result.findings, resource_ids)
				audit_run_repository.set_run_status(session, run, RUN_COMPLETED, completed=True)
				session.commit()

				logger.info(
					"Audit run %s completed: %s findings over %s records",
					run_id,
					len(result.findings),
					result.evaluated_record_count,
				)
			except Exception as exc:  # noqa: BLE001 - the run must record its own failure
				session.rollback()
				logger.exception("Audit run %s failed", run_id)
				run = audit_run_repository.get_run(session, run_id)
				if run is not None:
					audit_run_repository.set_run_status(session, run, RUN_FAILED, completed=True)
					session.commit()
				if self._jobs is not None:
					self._record_failure(run_id, str(exc))

	def _record_failure(self, run_id: int, message: str) -> None:
		"""``audit_runs`` has no error column, so failure text lives in the registry."""
		registry = self._jobs
		if registry is None:
			return
		key = ("audit_run", run_id)
		entry = registry.peek(key)
		if entry is not None:
			entry.state = "failed"
			entry.error = message

	def list_runs(
		self,
		session: Session,
		*,
		batch_id: int | None,
		status: str | None,
		page: int,
		page_size: int,
	) -> Tuple[List[AuditRunOut], int]:
		rows, total = audit_run_repository.list_runs(
			session, batch_id=batch_id, status=status, page=page, page_size=page_size
		)
		return [_run_out(row) for row in rows], total

	def detail(self, session: Session, run_id: int) -> AuditRunDetailOut:
		run = audit_run_repository.get_run(session, run_id)
		if run is None:
			raise NotFoundError(f"Audit run {run_id} was not found.")

		base = _run_out(run)
		error_message = None
		if self._jobs is not None:
			entry = self._jobs.peek(("audit_run", run_id))
			if entry is not None:
				error_message = entry.error

		return AuditRunDetailOut(
			**base.model_dump(),
			finding_count=audit_run_repository.count_findings(session, run_id),
			severity_counts=finding_repository.counts_for_run(session, run_id, FindingRow.severity),
			priority_counts=finding_repository.counts_for_run(session, run_id, FindingRow.priority),
			finding_type_counts=finding_repository.counts_for_run(
				session, run_id, FindingRow.finding_type
			),
			outcome_counts=finding_repository.counts_for_run(
				session, run_id, FindingRow.audit_outcome
			),
			error_message=error_message,
		)
