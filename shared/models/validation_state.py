from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class MissingRelationshipSignal:
	rule_id: str
	record_id: str
	resource_type: str
	relationship_field: str
	reason: str
	audit_only_note: str = "Audit-only governed relationship gap"


@dataclass(frozen=True)
class ResourceValidationState:
	record_id: str
	resource_type: str
	incomplete_fields: List[str] = field(default_factory=list)
	unresolved_links: List[str] = field(default_factory=list)
	rule_ready: bool = True
	governed_signals: List[MissingRelationshipSignal] = field(default_factory=list)

	@property
	def generic_incompleteness(self) -> bool:
		return bool(self.incomplete_fields or self.unresolved_links)
