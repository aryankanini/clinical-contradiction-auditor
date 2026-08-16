from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from module_4_api_ui.backend.disclaimers import (
	AI_AUDIT_ONLY_DISCLAIMER,
	RESOLUTION_AUDIT_ONLY_NOTE,
)


class EvidenceSynthesisOut(BaseModel):
	record_ids: List[str] = Field(default_factory=list)
	resource_types: List[str] = Field(default_factory=list)
	narrative: str = ""
	field_references: List[str] = Field(default_factory=list)


class ResolutionDraftOut(BaseModel):
	"""An AI-proposed action. Never actionable without human approval (FR-009)."""

	suggested_action: str
	rationale: str
	requires_human_approval: bool = True
	audit_only_note: str = RESOLUTION_AUDIT_ONLY_NOTE
	low_confidence: bool = False


class AIExplanationOut(BaseModel):
	"""AI rationale attached to a deterministic finding (FR-007).

	The disclaimer is a required field with a fixed default rather than optional copy,
	so no endpoint can return model-generated text without it (FR-011).
	"""

	id: int
	finding_id: int
	model_name: str
	prompt_version: str
	rationale_text: str
	confidence_context: str = ""
	evidence: EvidenceSynthesisOut | None = None
	resolution_draft: ResolutionDraftOut | None = None
	created_at: datetime
	low_confidence: bool = False
	disclaimer: str = AI_AUDIT_ONLY_DISCLAIMER


class ExplanationRequest(BaseModel):
	force_refresh: bool = False


class ExplanationJobOut(BaseModel):
	"""Transient generation state. The durable fact is whether a row exists."""

	finding_id: int
	state: Literal["pending", "running", "succeeded", "failed"]
	started_at: datetime | None = None
	completed_at: datetime | None = None
	error: str | None = None
