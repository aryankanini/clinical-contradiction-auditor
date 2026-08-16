from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from module_4_api_ui.backend.disclaimers import AUDIT_ONLY_NOTICE
from module_4_api_ui.backend.schemas.findings import FindingDetailOut


class SampleSelectRequest(BaseModel):
	audit_run_id: int | None = None
	batch_id: int | None = None
	severity: List[str] | None = None
	status: List[str] | None = None
	sample_size: int = Field(default=10, ge=1, le=500)
	seed: int = 20260816


class SampleOut(BaseModel):
	sample_id: str
	criteria: Dict[str, Any]
	finding_ids: List[int]
	candidate_count: int
	selected_at: datetime


class ReproducibilityCheckOut(BaseModel):
	name: str
	passed: bool
	detail: str


class ReproducibilityOut(BaseModel):
	"""FR-012: can this finding be rebuilt from stored artifacts alone?"""

	finding_id: int
	reproducible: bool
	checks: List[ReproducibilityCheckOut] = Field(default_factory=list)
	missing_artifacts: List[str] = Field(default_factory=list)
	verified_at: datetime


class VerificationRequest(BaseModel):
	outcome: Literal["passed", "failed"]
	notes: str | None = None


class VerificationOut(BaseModel):
	finding_id: int
	evidence_id: int
	outcome: str
	verified_by: str
	verified_at: datetime
	notes: str | None = None


class ExportRequest(BaseModel):
	finding_ids: List[int] = Field(min_length=1)
	include_replay_snapshots: bool = True


class EvidenceBundleItemOut(BaseModel):
	finding: FindingDetailOut
	batch_external_id: str | None = None
	rule_pack_version: str | None = None
	replay_snapshots: List[Dict[str, Any]] = Field(default_factory=list)
	reproducibility: ReproducibilityOut


class EvidenceBundleOut(BaseModel):
	sample_id: str
	generated_at: datetime
	generated_by: str
	items: List[EvidenceBundleItemOut] = Field(default_factory=list)
	export_path: str | None = None
	audit_only_notice: str = AUDIT_ONLY_NOTICE
