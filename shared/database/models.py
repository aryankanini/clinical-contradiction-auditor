from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base


JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class IngestBatchRow(Base):
	__tablename__ = "ingest_batches"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	batch_external_id: Mapped[str] = mapped_column(String(128), index=True)
	source_system: Mapped[str] = mapped_column(String(128), index=True)
	status: Mapped[str] = mapped_column(String(32), index=True)
	received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	accepted_count: Mapped[int] = mapped_column(Integer, default=0)
	quarantined_count: Mapped[int] = mapped_column(Integer, default=0)
	loader_success_count: Mapped[int] = mapped_column(Integer, default=0)
	loader_failure_count: Mapped[int] = mapped_column(Integer, default=0)
	provenance_artifact_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
	replay_artifact_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

	records: Mapped[list["IngestRecordRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
	audit_runs: Mapped[list["AuditRunRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class IngestRecordRow(Base):
	__tablename__ = "ingest_records"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batches.id"), index=True)
	resource_type: Mapped[str] = mapped_column(String(64), index=True)
	resource_family: Mapped[str] = mapped_column(String(64), index=True)
	record_external_id: Mapped[str] = mapped_column(String(128), index=True)
	raw_payload: Mapped[dict] = mapped_column(JSON_TYPE)
	quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
	quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

	batch: Mapped[IngestBatchRow] = relationship(back_populates="records")
	normalized_resource: Mapped["NormalizedResourceRow | None"] = relationship(back_populates="ingest_record", cascade="all, delete-orphan")


class NormalizedResourceRow(Base):
	__tablename__ = "normalized_resources"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batches.id"), index=True)
	ingest_record_id: Mapped[int] = mapped_column(ForeignKey("ingest_records.id"), unique=True, index=True)
	resource_type: Mapped[str] = mapped_column(String(64), index=True)
	record_external_id: Mapped[str] = mapped_column(String(128), index=True)
	status_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
	status_state: Mapped[str] = mapped_column(String(32), index=True)
	primary_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	timestamps: Mapped[dict] = mapped_column(JSON_TYPE)
	references: Mapped[dict] = mapped_column(JSON_TYPE)
	provenance: Mapped[dict] = mapped_column(JSON_TYPE)

	ingest_record: Mapped[IngestRecordRow] = relationship(back_populates="normalized_resource")
	validation_state: Mapped["ValidationStateRow | None"] = relationship(back_populates="normalized_resource", cascade="all, delete-orphan")
	finding_evidence: Mapped[list["FindingEvidenceRow"]] = relationship(back_populates="normalized_resource")


class ValidationStateRow(Base):
	__tablename__ = "validation_states"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	normalized_resource_id: Mapped[int] = mapped_column(ForeignKey("normalized_resources.id"), unique=True, index=True)
	rule_ready: Mapped[bool] = mapped_column(Boolean, index=True)
	incomplete_fields: Mapped[list] = mapped_column(JSON_TYPE)
	unresolved_links: Mapped[list] = mapped_column(JSON_TYPE)

	normalized_resource: Mapped[NormalizedResourceRow] = relationship(back_populates="validation_state")
	governed_signals: Mapped[list["GovernedRelationshipSignalRow"]] = relationship(back_populates="validation_state", cascade="all, delete-orphan")


class GovernedRelationshipSignalRow(Base):
	__tablename__ = "governed_relationship_signals"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	validation_state_id: Mapped[int] = mapped_column(ForeignKey("validation_states.id"), index=True)
	rule_id: Mapped[str] = mapped_column(String(128), index=True)
	relationship_field: Mapped[str] = mapped_column(String(128), index=True)
	reason: Mapped[str] = mapped_column(Text)
	audit_only_note: Mapped[str] = mapped_column(Text)

	validation_state: Mapped[ValidationStateRow] = relationship(back_populates="governed_signals")


class RulePackRow(Base):
	__tablename__ = "rule_packs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	version: Mapped[str] = mapped_column(String(64), unique=True, index=True)
	status: Mapped[str] = mapped_column(String(32), index=True)
	published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	metadata_json: Mapped[dict] = mapped_column(JSON_TYPE)

	audit_runs: Mapped[list["AuditRunRow"]] = relationship(back_populates="rule_pack")


class AuditRunRow(Base):
	__tablename__ = "audit_runs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	batch_id: Mapped[int] = mapped_column(ForeignKey("ingest_batches.id"), index=True)
	rule_pack_id: Mapped[int] = mapped_column(ForeignKey("rule_packs.id"), index=True)
	status: Mapped[str] = mapped_column(String(32), index=True)
	started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	batch: Mapped[IngestBatchRow] = relationship(back_populates="audit_runs")
	rule_pack: Mapped[RulePackRow] = relationship(back_populates="audit_runs")
	findings: Mapped[list["FindingRow"]] = relationship(back_populates="audit_run", cascade="all, delete-orphan")


class FindingRow(Base):
	__tablename__ = "findings"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	audit_run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id"), index=True)
	rule_id: Mapped[str] = mapped_column(String(128), index=True)
	severity: Mapped[str] = mapped_column(String(32), index=True)
	priority: Mapped[str] = mapped_column(String(32), index=True)
	finding_type: Mapped[str] = mapped_column(String(64), index=True)
	status: Mapped[str] = mapped_column(String(32), index=True)
	summary: Mapped[str] = mapped_column(Text)
	audit_outcome: Mapped[str] = mapped_column(String(64), index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	audit_run: Mapped[AuditRunRow] = relationship(back_populates="findings")
	evidence_items: Mapped[list["FindingEvidenceRow"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
	assignments: Mapped[list["FindingAssignmentRow"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
	status_history: Mapped[list["FindingStatusHistoryRow"]] = relationship(back_populates="finding", cascade="all, delete-orphan")
	ai_explanations: Mapped[list["AIExplanationRow"]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class FindingEvidenceRow(Base):
	__tablename__ = "finding_evidence"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
	normalized_resource_id: Mapped[int | None] = mapped_column(ForeignKey("normalized_resources.id"), nullable=True, index=True)
	evidence_type: Mapped[str] = mapped_column(String(64), index=True)
	evidence_payload: Mapped[dict] = mapped_column(JSON_TYPE)

	finding: Mapped[FindingRow] = relationship(back_populates="evidence_items")
	normalized_resource: Mapped[NormalizedResourceRow | None] = relationship(back_populates="finding_evidence")


class ResolutionQueueRow(Base):
	__tablename__ = "resolution_queues"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	name: Mapped[str] = mapped_column(String(128), unique=True)
	owner_type: Mapped[str] = mapped_column(String(64), index=True)
	config_json: Mapped[dict] = mapped_column(JSON_TYPE)

	assignments: Mapped[list["FindingAssignmentRow"]] = relationship(back_populates="queue")


class FindingAssignmentRow(Base):
	__tablename__ = "finding_assignments"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
	queue_id: Mapped[int] = mapped_column(ForeignKey("resolution_queues.id"), index=True)
	assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
	assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	finding: Mapped[FindingRow] = relationship(back_populates="assignments")
	queue: Mapped[ResolutionQueueRow] = relationship(back_populates="assignments")


class FindingStatusHistoryRow(Base):
	__tablename__ = "finding_status_history"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
	from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
	to_status: Mapped[str] = mapped_column(String(32), index=True)
	changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)

	finding: Mapped[FindingRow] = relationship(back_populates="status_history")


class AIExplanationRow(Base):
	__tablename__ = "ai_explanations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
	model_name: Mapped[str] = mapped_column(String(128))
	prompt_version: Mapped[str] = mapped_column(String(64))
	rationale_text: Mapped[str] = mapped_column(Text)
	confidence_json: Mapped[dict] = mapped_column(JSON_TYPE)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	finding: Mapped[FindingRow] = relationship(back_populates="ai_explanations")
