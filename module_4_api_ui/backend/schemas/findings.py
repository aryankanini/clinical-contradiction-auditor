from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from module_4_api_ui.backend.disclaimers import AUDIT_ONLY_NOTICE
from module_4_api_ui.backend.schemas.explanations import AIExplanationOut
from module_4_api_ui.backend.schemas.resolution import AssignmentOut, ResolutionOut


class TransparencyOut(BaseModel):
	"""The FR-006 audit transparency payload.

	FR-006 names exactly what every finding must carry: rule ID, records evaluated,
	evidence references, timestamp, and audit outcome. ``complete`` and
	``missing_fields`` make the BRD's "90% of findings with complete transparency
	fields" measurable, and drive UC-002 extension 2a, which blocks acceptance of a
	finding whose transparency is incomplete.
	"""

	rule_id: str
	rule_pack_version: str | None
	audit_run_id: int
	records_evaluated: List[str] = Field(default_factory=list)
	evidence_refs: List[str] = Field(default_factory=list)
	detected_at: datetime
	audit_outcome: str
	ai_rationale_present: bool = False
	ai_confidence_context: str | None = None
	ai_model_name: str | None = None
	ai_prompt_version: str | None = None
	replay_artifact_path: str | None = None
	complete: bool = False
	missing_fields: List[str] = Field(default_factory=list)


class FindingEvidenceOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	evidence_type: str
	normalized_resource_id: int | None = None
	record_external_id: str | None = None
	resource_type: str | None = None
	status_value: str | None = None
	status_state: str | None = None
	primary_timestamp: datetime | None = None
	evidence_payload: Dict[str, Any] = Field(default_factory=dict)


class StatusHistoryOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	from_status: str | None
	to_status: str
	changed_at: datetime
	changed_by: str | None
	notes: str | None


class FindingSummaryOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	audit_run_id: int
	rule_id: str
	finding_type: str
	severity: str
	priority: str
	status: str
	summary: str
	audit_outcome: str
	created_at: datetime
	evidence_count: int = 0
	has_explanation: bool = False
	transparency_complete: bool = False
	assigned_queue_name: str | None = None
	assigned_to: str | None = None


class FindingDetailOut(FindingSummaryOut):
	transparency: TransparencyOut
	evidence: List[FindingEvidenceOut] = Field(default_factory=list)
	explanation: AIExplanationOut | None = None
	resolution: ResolutionOut | None = None
	assignment: AssignmentOut | None = None
	status_history: List[StatusHistoryOut] = Field(default_factory=list)
	allowed_transitions: List[str] = Field(default_factory=list)
	audit_only_notice: str = AUDIT_ONLY_NOTICE


class TriageRequest(BaseModel):
	disposition: Literal["accept", "defer", "escalate", "dispute"]
	notes: str | None = None


class StatusTransitionRequest(BaseModel):
	to_status: str
	notes: str | None = None


class FindingStatsOut(BaseModel):
	total: int
	open_total: int
	by_severity: Dict[str, int] = Field(default_factory=dict)
	by_status: Dict[str, int] = Field(default_factory=dict)
	by_priority: Dict[str, int] = Field(default_factory=dict)
	by_finding_type: Dict[str, int] = Field(default_factory=dict)
	transparency_complete_count: int = 0
