from __future__ import annotations

"""Queries over the ingestion tables.

``IngestionDatabaseStore`` in module 1 is write-only, so every read in the API is
defined here.
"""

from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from shared.database.models import (
	AuditRunRow,
	GovernedRelationshipSignalRow,
	IngestBatchRow,
	NormalizedResourceRow,
	ValidationStateRow,
)


def get_batch(session: Session, batch_id: int) -> IngestBatchRow | None:
	return session.get(IngestBatchRow, batch_id)


def get_batch_by_external_id(session: Session, external_id: str) -> IngestBatchRow | None:
	statement = (
		select(IngestBatchRow)
		.where(IngestBatchRow.batch_external_id == external_id)
		.order_by(IngestBatchRow.id.desc())
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def list_batches(
	session: Session,
	*,
	status: str | None = None,
	source: str | None = None,
	page: int = 1,
	page_size: int = 25,
) -> Tuple[List[IngestBatchRow], int]:
	filters = []
	if status:
		filters.append(IngestBatchRow.status == status)
	if source:
		filters.append(IngestBatchRow.source_system == source)

	total = session.execute(
		select(func.count()).select_from(IngestBatchRow).where(*filters)
	).scalar_one()

	statement = (
		select(IngestBatchRow)
		.where(*filters)
		.order_by(IngestBatchRow.received_at.desc(), IngestBatchRow.id.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	return list(session.execute(statement).scalars().all()), int(total)


def resource_type_counts(session: Session, batch_id: int) -> Dict[str, int]:
	statement = (
		select(NormalizedResourceRow.resource_type, func.count())
		.where(NormalizedResourceRow.batch_id == batch_id)
		.group_by(NormalizedResourceRow.resource_type)
	)
	return {row[0]: int(row[1]) for row in session.execute(statement).all()}


def rule_ready_count(session: Session, batch_id: int) -> int:
	statement = (
		select(func.count())
		.select_from(ValidationStateRow)
		.join(NormalizedResourceRow, ValidationStateRow.normalized_resource_id == NormalizedResourceRow.id)
		.where(NormalizedResourceRow.batch_id == batch_id, ValidationStateRow.rule_ready.is_(True))
	)
	return int(session.execute(statement).scalar_one())


def governed_signal_count(session: Session, batch_id: int) -> int:
	statement = (
		select(func.count())
		.select_from(GovernedRelationshipSignalRow)
		.join(
			ValidationStateRow,
			GovernedRelationshipSignalRow.validation_state_id == ValidationStateRow.id,
		)
		.join(
			NormalizedResourceRow,
			ValidationStateRow.normalized_resource_id == NormalizedResourceRow.id,
		)
		.where(NormalizedResourceRow.batch_id == batch_id)
	)
	return int(session.execute(statement).scalar_one())


def list_audit_runs_for_batch(session: Session, batch_id: int) -> List[AuditRunRow]:
	statement = (
		select(AuditRunRow)
		.where(AuditRunRow.batch_id == batch_id)
		.options(selectinload(AuditRunRow.rule_pack))
		.order_by(AuditRunRow.started_at.desc(), AuditRunRow.id.desc())
	)
	return list(session.execute(statement).scalars().all())


def list_normalized_resources(
	session: Session,
	batch_id: int,
	*,
	resource_type: str | None = None,
	rule_ready: bool | None = None,
	page: int = 1,
	page_size: int = 50,
) -> Tuple[List[NormalizedResourceRow], int]:
	filters = [NormalizedResourceRow.batch_id == batch_id]
	if resource_type:
		filters.append(NormalizedResourceRow.resource_type == resource_type)

	statement = select(NormalizedResourceRow).where(*filters)
	count_statement = select(func.count()).select_from(NormalizedResourceRow).where(*filters)

	if rule_ready is not None:
		statement = statement.join(
			ValidationStateRow,
			ValidationStateRow.normalized_resource_id == NormalizedResourceRow.id,
		).where(ValidationStateRow.rule_ready.is_(rule_ready))
		count_statement = count_statement.join(
			ValidationStateRow,
			ValidationStateRow.normalized_resource_id == NormalizedResourceRow.id,
		).where(ValidationStateRow.rule_ready.is_(rule_ready))

	total = session.execute(count_statement).scalar_one()

	statement = (
		statement.options(
			selectinload(NormalizedResourceRow.validation_state).selectinload(
				ValidationStateRow.governed_signals
			)
		)
		.order_by(NormalizedResourceRow.id)
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	return list(session.execute(statement).scalars().all()), int(total)


def _flatten_timestamps(raw: Any) -> Dict[str, Any]:
	"""Reduce the stored ``{name: {value, state, source_path}}`` map to ``{name: value}``.

	This is the same flattening ``ReplayArtifact.snapshots`` performs, which is what
	keeps one record shape flowing from ingest through the engine to module 3.
	"""
	if not isinstance(raw, dict):
		return {}
	flattened: Dict[str, Any] = {}
	for name, field in raw.items():
		if isinstance(field, dict):
			flattened[name] = field.get("value")
		else:
			flattened[name] = field
	return flattened


def load_audit_inputs(session: Session, batch_id: int) -> List[Dict[str, Any]]:
	"""Build the engine's input records for one batch.

	References keep their full ``{reference, target_id, state}`` structure rather than
	being flattened to a string, because FR-005 relationship rules need the resolution
	state, not just presence.
	"""
	statement = (
		select(NormalizedResourceRow)
		.where(NormalizedResourceRow.batch_id == batch_id)
		.options(
			selectinload(NormalizedResourceRow.validation_state).selectinload(
				ValidationStateRow.governed_signals
			),
			selectinload(NormalizedResourceRow.ingest_record),
		)
		.order_by(NormalizedResourceRow.record_external_id)
	)
	rows = session.execute(statement).scalars().all()

	records: List[Dict[str, Any]] = []
	for row in rows:
		state = row.validation_state
		family = row.ingest_record.resource_family if row.ingest_record else row.resource_type
		records.append(
			{
				"record_id": row.record_external_id,
				"resource_type": row.resource_type,
				"family": family,
				"status": row.status_value,
				"status_state": row.status_state,
				"timestamps": _flatten_timestamps(row.timestamps),
				"references": dict(row.references or {}),
				"raw_payload": dict(row.ingest_record.raw_payload or {}) if row.ingest_record else {},
				"incomplete_fields": list(state.incomplete_fields or []) if state else [],
				"unresolved_links": list(state.unresolved_links or []) if state else [],
				"governed_signals": [signal.rule_id for signal in state.governed_signals]
				if state
				else [],
				"rule_ready": bool(state.rule_ready) if state else True,
				"normalized_resource_id": row.id,
			}
		)
	return records


def resources_by_external_id(
	session: Session,
	batch_id: int,
	external_ids: Sequence[str],
) -> Dict[str, NormalizedResourceRow]:
	if not external_ids:
		return {}
	statement = select(NormalizedResourceRow).where(
		NormalizedResourceRow.batch_id == batch_id,
		NormalizedResourceRow.record_external_id.in_(list(external_ids)),
	)
	return {
		row.record_external_id: row for row in session.execute(statement).scalars().all()
	}
