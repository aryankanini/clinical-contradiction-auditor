from __future__ import annotations

"""The contract module 2 must satisfy to replace the placeholder engine.

``module_2_audit_engine`` does NOT import this file — it only needs to expose a class
whose ``evaluate_batch`` matches this shape and whose result types come from
``shared.models.audit_finding``. That keeps the dependency one-directional.

The input is a list of plain dicts rather than ORM rows on purpose: that dict shape is
already canonical in this repo. It is exactly what ``ReplayArtifact.snapshots`` stores
(``module_1_data/pipeline.py``) and exactly what module 3's ``evidence_records``
consumes (``module_3_ai_reasoning/agents/evidence_agent.py``). One shape flows
ingest -> engine -> AI -> API, so no adapter is needed at any hop.
"""

from typing import Any, Mapping, Protocol, Sequence, Tuple, runtime_checkable

from shared.models.audit_finding import AuditEngineResult


# The keys every audit input record carries. ``normalized_resource_id`` is added by
# module 4 so evidence can be linked back to a row; an engine may ignore it.
AUDIT_INPUT_KEYS: Tuple[str, ...] = (
	"record_id",
	"resource_type",
	"family",
	"status",
	"status_state",
	"timestamps",
	"references",
	"incomplete_fields",
	"unresolved_links",
	"governed_signals",
	"rule_ready",
	"normalized_resource_id",
)


@runtime_checkable
class AuditEnginePort(Protocol):
	"""Deterministic contradiction detection (FR-003, FR-004, FR-005)."""

	@property
	def rule_pack_version(self) -> str:
		"""Version string recorded on every run and finding for traceability."""
		...

	def evaluate_batch(
		self,
		resources: Sequence[Mapping[str, Any]],
		rule_pack: Mapping[str, Any],
	) -> AuditEngineResult:
		"""Evaluate one batch of normalized resources.

		Must be deterministic: the same input yields byte-identical findings, which is
		what makes FR-012 reproducibility possible. Pure CPU work, no I/O — the caller
		runs it in a worker thread.
		"""
		...
