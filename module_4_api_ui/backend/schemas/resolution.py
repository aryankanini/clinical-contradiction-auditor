from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from module_4_api_ui.backend.disclaimers import RESOLUTION_AUDIT_ONLY_NOTE


class ResolutionApprovalRequest(BaseModel):
	"""A human's decision on a resolution (FR-009).

	``source`` records whether the text came from the model, was edited by the steward,
	or was written from scratch — the distinction compliance review needs.
	"""

	suggested_action: str = Field(min_length=1)
	rationale: str = Field(min_length=1)
	source: Literal["ai", "ai_edited", "manual"]
	notes: str | None = None


class ResolutionOut(BaseModel):
	evidence_id: int
	suggested_action: str
	rationale: str
	source: str
	approved_by: str
	approved_at: datetime
	notes: str | None = None
	audit_only_note: str = RESOLUTION_AUDIT_ONLY_NOTE


class AssignmentRequest(BaseModel):
	queue_id: int | None = None
	assigned_to: str | None = None


class AssignmentOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	queue_id: int
	queue_name: str
	owner_type: str
	assigned_to: str | None = None
	assigned_at: datetime
	auto_routed: bool = False
	escalated: bool = False
