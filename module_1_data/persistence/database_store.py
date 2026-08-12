from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from sqlalchemy.orm import Session, sessionmaker

from shared.database.models import (
	GovernedRelationshipSignalRow,
	IngestBatchRow,
	IngestRecordRow,
	NormalizedResourceRow,
	ValidationStateRow,
)
from shared.models.staged_resource import IngestRunResult, StagedResource


def _parse_datetime(value: Any) -> datetime | None:
	if not isinstance(value, str) or not value:
		return None
	try:
		return datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return None


class IngestionDatabaseStore:
	def __init__(self, session_factory: sessionmaker[Session]) -> None:
		self._session_factory = session_factory

	def persist_ingest_run(self, payload: Mapping[str, Any], result: IngestRunResult) -> int:
		with self._session_factory() as session:
			batch_row = IngestBatchRow(
				batch_external_id=str(result.metadata.get("batch_id", payload.get("batch_id", "unknown"))),
				source_system=str(result.metadata.get("source", payload.get("source", "unknown"))),
				status=result.status,
				accepted_count=int(result.metadata.get("accepted_count", 0)),
				quarantined_count=int(result.metadata.get("quarantined_count", 0)),
				loader_success_count=int(result.metadata.get("loader_success_count", 0)),
				loader_failure_count=int(result.metadata.get("loader_failure_count", 0)),
				provenance_artifact_path=result.provenance.storage_path if result.provenance else None,
				replay_artifact_path=result.replay_artifact.storage_path if result.replay_artifact else None,
			)
			session.add(batch_row)
			session.flush()

			record_rows_by_external_id: dict[str, IngestRecordRow] = {}
			for staged in result.staged_resources:
				record_row = self._build_ingest_record_row(batch_row.id, staged, quarantined=False, quarantine_reason=None)
				session.add(record_row)
				session.flush()
				record_rows_by_external_id[staged.record_id] = record_row

			for record in result.quarantined_records:
				record_id = str(record.get("id", f"quarantined-{len(record_rows_by_external_id)}"))
				record_rows_by_external_id[record_id] = IngestRecordRow(
					batch_id=batch_row.id,
					resource_type=str(record.get("resourceType", "unknown")),
					resource_family="unknown",
					record_external_id=record_id,
					raw_payload=dict(record),
					quarantined=True,
					quarantine_reason=self._quarantine_reason_for_record(record_id, result.validation_errors),
				)
				session.add(record_rows_by_external_id[record_id])
				session.flush()

			validation_by_record_id = {state.record_id: state for state in result.validation_states}
			for normalized in result.normalized_resources:
				record_row = record_rows_by_external_id[normalized.record_id]
				normalized_row = NormalizedResourceRow(
					batch_id=batch_row.id,
					ingest_record_id=record_row.id,
					resource_type=normalized.resource_type,
					record_external_id=normalized.record_id,
					status_value=normalized.status.value,
					status_state=normalized.status.state.value,
					primary_timestamp=_parse_datetime(normalized.primary_timestamp.value),
					timestamps={name: {"value": field.value, "state": field.state.value, "source_path": field.source_path} for name, field in normalized.timestamps.items()},
					references={name: {"reference": ref.reference, "target_id": ref.target_id, "state": ref.state.value, "source_path": ref.source_path} for name, ref in normalized.references.items()},
					provenance=dict(normalized.provenance),
				)
				session.add(normalized_row)
				session.flush()

				validation_state = validation_by_record_id[normalized.record_id]
				validation_row = ValidationStateRow(
					normalized_resource_id=normalized_row.id,
					rule_ready=validation_state.rule_ready,
					incomplete_fields=list(validation_state.incomplete_fields),
					unresolved_links=list(validation_state.unresolved_links),
				)
				session.add(validation_row)
				session.flush()

				for signal in validation_state.governed_signals:
					session.add(
						GovernedRelationshipSignalRow(
							validation_state_id=validation_row.id,
							rule_id=signal.rule_id,
							relationship_field=signal.relationship_field,
							reason=signal.reason,
							audit_only_note=signal.audit_only_note,
						)
					)

			session.commit()
			return batch_row.id

	@staticmethod
	def _build_ingest_record_row(
		batch_id: int,
		staged: StagedResource,
		quarantined: bool,
		quarantine_reason: str | None,
	) -> IngestRecordRow:
		return IngestRecordRow(
			batch_id=batch_id,
			resource_type=staged.resource_type,
			resource_family=staged.family,
			record_external_id=staged.record_id,
			raw_payload=dict(staged.payload),
			quarantined=quarantined,
			quarantine_reason=quarantine_reason,
		)

	@staticmethod
	def _quarantine_reason_for_record(record_id: str, validation_errors: list[dict[str, Any]]) -> str | None:
		for error in validation_errors:
			if error.get("record_id") == record_id:
				return str(error.get("reason"))
		return None
