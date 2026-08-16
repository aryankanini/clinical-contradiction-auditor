from __future__ import annotations

"""Batch ingestion and read use cases (UC-001)."""

from typing import Any, Dict, List, Mapping, Tuple

from sqlalchemy.orm import Session

from module_1_data.pipeline import ingest_batch
from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.errors import NotFoundError, ValidationError
from module_4_api_ui.backend.repositories import batch_repository
from module_4_api_ui.backend.schemas.batches import (
	AuditRunSummaryOut,
	BatchDetailOut,
	BatchIngestResponse,
	BatchSummaryOut,
	GovernedSignalOut,
	NormalizedResourceOut,
)
from shared.database.models import AuditRunRow, IngestBatchRow, NormalizedResourceRow


def _run_summary(run: AuditRunRow) -> AuditRunSummaryOut:
	return AuditRunSummaryOut(
		id=run.id,
		status=run.status,
		started_at=run.started_at,
		completed_at=run.completed_at,
		rule_pack_version=run.rule_pack.version if run.rule_pack else None,
	)


class BatchService:
	"""Wraps module 1's pipeline and the ingestion read model."""

	def __init__(self, config: ApiConfig) -> None:
		self._config = config

	# --- writes ---------------------------------------------------------

	def ingest(self, session: Session, payload: Mapping[str, Any]) -> BatchIngestResponse:
		"""Run the real ingestion pipeline and return its outcome.

		``ingest_batch`` builds and disposes its own engine from a URL string, so this
		cannot join the request's transaction. That is module 1's design; the API just
		reads back the committed rows afterwards.
		"""
		records = payload.get("records")
		if isinstance(records, list) and len(records) > self._config.max_batch_records:
			raise ValidationError(
				f"Batch exceeds the {self._config.max_batch_records}-record limit.",
				context={
					"record_count": len(records),
					"max_batch_records": self._config.max_batch_records,
				},
			)

		result = ingest_batch(
			payload,
			artifact_dir=self._config.artifact_dir,
			database_url=self._config.database_url,
		)

		database_batch_id = result.metadata.get("database_batch_id")
		if database_batch_id is None:
			# Nothing was accepted, so module 1 never wrote a batch row.
			raise ValidationError(
				"Batch was rejected before persistence.",
				context={
					"ingest_status": result.status,
					"validation_errors": result.validation_errors,
					"metadata": dict(result.metadata),
				},
			)

		session.expire_all()
		batch = batch_repository.get_batch(session, int(database_batch_id))
		if batch is None:
			raise NotFoundError(f"Ingested batch {database_batch_id} could not be read back.")

		return BatchIngestResponse(
			batch=self.detail(session, batch.id),
			ingest_status=result.status,
			validation_errors=list(result.validation_errors),
			quarantined_records=[dict(record) for record in result.quarantined_records],
			loader_failures=list(result.loader_failures),
			provenance_id=result.provenance.provenance_id if result.provenance else None,
			replay_artifact_id=result.replay_artifact.artifact_id if result.replay_artifact else None,
		)

	# --- reads ----------------------------------------------------------

	def list_batches(
		self,
		session: Session,
		*,
		status: str | None,
		source: str | None,
		page: int,
		page_size: int,
	) -> Tuple[List[BatchSummaryOut], int]:
		rows, total = batch_repository.list_batches(
			session, status=status, source=source, page=page, page_size=page_size
		)
		summaries = [self._summary(session, row) for row in rows]
		return summaries, total

	def _summary(self, session: Session, batch: IngestBatchRow) -> BatchSummaryOut:
		runs = batch_repository.list_audit_runs_for_batch(session, batch.id)
		return BatchSummaryOut(
			id=batch.id,
			batch_external_id=batch.batch_external_id,
			source_system=batch.source_system,
			status=batch.status,
			received_at=batch.received_at,
			accepted_count=batch.accepted_count,
			quarantined_count=batch.quarantined_count,
			loader_success_count=batch.loader_success_count,
			loader_failure_count=batch.loader_failure_count,
			latest_audit_run=_run_summary(runs[0]) if runs else None,
		)

	def detail(self, session: Session, batch_id: int) -> BatchDetailOut:
		batch = batch_repository.get_batch(session, batch_id)
		if batch is None:
			raise NotFoundError(f"Batch {batch_id} was not found.")

		runs = batch_repository.list_audit_runs_for_batch(session, batch.id)
		return BatchDetailOut(
			id=batch.id,
			batch_external_id=batch.batch_external_id,
			source_system=batch.source_system,
			status=batch.status,
			received_at=batch.received_at,
			accepted_count=batch.accepted_count,
			quarantined_count=batch.quarantined_count,
			loader_success_count=batch.loader_success_count,
			loader_failure_count=batch.loader_failure_count,
			latest_audit_run=_run_summary(runs[0]) if runs else None,
			provenance_artifact_path=batch.provenance_artifact_path,
			replay_artifact_path=batch.replay_artifact_path,
			resource_type_counts=batch_repository.resource_type_counts(session, batch.id),
			rule_ready_count=batch_repository.rule_ready_count(session, batch.id),
			governed_signal_count=batch_repository.governed_signal_count(session, batch.id),
			audit_runs=[_run_summary(run) for run in runs],
		)

	def list_resources(
		self,
		session: Session,
		batch_id: int,
		*,
		resource_type: str | None,
		rule_ready: bool | None,
		page: int,
		page_size: int,
	) -> Tuple[List[NormalizedResourceOut], int]:
		if batch_repository.get_batch(session, batch_id) is None:
			raise NotFoundError(f"Batch {batch_id} was not found.")

		rows, total = batch_repository.list_normalized_resources(
			session,
			batch_id,
			resource_type=resource_type,
			rule_ready=rule_ready,
			page=page,
			page_size=page_size,
		)
		return [self._resource_out(row) for row in rows], total

	@staticmethod
	def _resource_out(row: NormalizedResourceRow) -> NormalizedResourceOut:
		state = row.validation_state
		return NormalizedResourceOut(
			id=row.id,
			resource_type=row.resource_type,
			record_external_id=row.record_external_id,
			status_value=row.status_value,
			status_state=row.status_state,
			primary_timestamp=row.primary_timestamp,
			timestamps=dict(row.timestamps or {}),
			references=dict(row.references or {}),
			provenance=dict(row.provenance or {}),
			rule_ready=bool(state.rule_ready) if state else True,
			incomplete_fields=list(state.incomplete_fields or []) if state else [],
			unresolved_links=list(state.unresolved_links or []) if state else [],
			governed_signals=[
				GovernedSignalOut(
					rule_id=signal.rule_id,
					relationship_field=signal.relationship_field,
					reason=signal.reason,
					audit_only_note=signal.audit_only_note,
				)
				for signal in (state.governed_signals if state else [])
			],
		)
