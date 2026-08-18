from __future__ import annotations

"""Contract types exchanged between the audit engine and the API.

These live in ``shared`` so ``module_2_audit_engine`` can produce them without
importing anything from ``module_4_api_ui`` — the dependency points one way only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class DetectedEvidence:
	"""One record or signal supporting a detected finding."""

	evidence_type: str
	record_external_id: str | None = None
	normalized_resource_id: int | None = None
	payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectedFinding:
	"""A contradiction established by deterministic rule evaluation (FR-003)."""

	rule_id: str
	finding_type: str
	severity: str
	priority: str
	summary: str
	audit_outcome: str
	evidence: List[DetectedEvidence] = field(default_factory=list)
	rule_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEngineResult:
	"""Everything one engine pass produced for a single batch."""

	rule_pack_version: str
	findings: List[DetectedFinding] = field(default_factory=list)
	evaluated_record_count: int = 0
	skipped_record_count: int = 0
