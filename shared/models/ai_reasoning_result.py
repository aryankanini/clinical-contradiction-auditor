from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EvidenceSynthesis:
	record_ids: List[str]
	resource_types: List[str]
	narrative: str
	field_references: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionDraft:
	suggested_action: str
	rationale: str
	requires_human_approval: bool = True
	audit_only_note: str = "This draft is non-diagnostic and requires human review before any action is taken."


@dataclass(frozen=True)
class AIReasoningResult:
	finding_id: str
	rule_id: str
	contradiction_explanation: str
	confidence_context: str
	evidence: EvidenceSynthesis
	resolution_draft: ResolutionDraft
	model_name: str
	prompt_version: str
	metadata: Dict[str, Any] = field(default_factory=dict)
