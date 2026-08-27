from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class GovernedSignalOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	rule_id: str
	relationship_field: str
	reason: str
	audit_only_note: str


class NormalizedResourceOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	resource_type: str
	record_external_id: str
	status_value: str | None
	status_state: str
	primary_timestamp: datetime | None
	timestamps: Dict[str, Any]
	references: Dict[str, Any]
	provenance: Dict[str, Any]
	rule_ready: bool = True
	incomplete_fields: List[str] = Field(default_factory=list)
	unresolved_links: List[str] = Field(default_factory=list)
	governed_signals: List[GovernedSignalOut] = Field(default_factory=list)


class AuditRunSummaryOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	status: str
	started_at: datetime
	completed_at: datetime | None
	rule_pack_version: str | None = None


class BatchSummaryOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	batch_external_id: str
	source_system: str
	status: str
	received_at: datetime
	accepted_count: int
	quarantined_count: int
	loader_success_count: int
	loader_failure_count: int
	latest_audit_run: AuditRunSummaryOut | None = None


class BatchDetailOut(BatchSummaryOut):
	provenance_artifact_path: str | None = None
	replay_artifact_path: str | None = None
	resource_type_counts: Dict[str, int] = Field(default_factory=dict)
	rule_ready_count: int = 0
	governed_signal_count: int = 0
	audit_runs: List[AuditRunSummaryOut] = Field(default_factory=list)


class BatchIngestResponse(BaseModel):
	"""Ingest outcome, including everything that did not make it through."""

	batch: BatchDetailOut
	ingest_status: str
	validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
	quarantined_records: List[Dict[str, Any]] = Field(default_factory=list)
	loader_failures: List[Dict[str, Any]] = Field(default_factory=list)
	provenance_id: str | None = None
	replay_artifact_id: str | None = None
