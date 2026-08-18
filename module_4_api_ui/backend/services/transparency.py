from __future__ import annotations

"""FR-006 audit transparency assembly.

FR-006 requires every finding to carry rule ID, records evaluated, evidence references,
timestamp, and audit outcome. This module builds that payload and reports which of the
required fields are missing, which is what makes the BRD's "90% of findings with
complete transparency fields" target measurable rather than aspirational.
"""

import json
from typing import Any, Dict, List, Tuple

from module_4_api_ui.backend.constants import ENGINE_EVIDENCE_TYPES
from module_4_api_ui.backend.schemas.findings import TransparencyOut
from shared.database.models import AIExplanationRow, FindingRow


def _explanation_payload(explanation: AIExplanationRow | None) -> Dict[str, Any]:
	if explanation is None:
		return {}
	raw = explanation.confidence_json
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except ValueError:
			return {}
	return raw if isinstance(raw, dict) else {}


def build_transparency(
	finding: FindingRow,
	explanation: AIExplanationRow | None,
	*,
	rule_pack_version: str | None,
	replay_artifact_path: str | None,
) -> TransparencyOut:
	evidence_items = [
		item for item in finding.evidence_items if item.evidence_type in ENGINE_EVIDENCE_TYPES
	]

	records_evaluated: List[str] = []
	evidence_refs: List[str] = []
	for item in evidence_items:
		evidence_refs.append(f"finding_evidence:{item.id}")
		if item.normalized_resource is not None:
			record_id = item.normalized_resource.record_external_id
		else:
			record_id = str(item.evidence_payload.get("record_id") or "") or None
		if record_id and record_id not in records_evaluated:
			records_evaluated.append(record_id)

	payload = _explanation_payload(explanation)
	confidence_context = str(payload.get("confidence_context") or "").strip()

	missing: List[str] = []
	if not finding.rule_id:
		missing.append("rule_id")
	if not records_evaluated:
		missing.append("records_evaluated")
	if not evidence_refs:
		missing.append("evidence")
	if not finding.audit_outcome:
		missing.append("audit_outcome")
	if explanation is None or not (explanation.rationale_text or "").strip():
		missing.append("ai_rationale")
	# Module 3 derives confidence context by splitting the model's response on a literal
	# marker; when the model deviates the field silently comes back empty. Treating that
	# as a missing transparency field is what keeps the gap visible instead of shipping
	# a finding that merely looks complete.
	if not confidence_context:
		missing.append("ai_confidence_context")

	return TransparencyOut(
		rule_id=finding.rule_id,
		rule_pack_version=rule_pack_version,
		audit_run_id=finding.audit_run_id,
		records_evaluated=records_evaluated,
		evidence_refs=evidence_refs,
		detected_at=finding.created_at,
		audit_outcome=finding.audit_outcome,
		ai_rationale_present=explanation is not None
		and bool((explanation.rationale_text or "").strip()),
		ai_confidence_context=confidence_context or None,
		ai_model_name=explanation.model_name if explanation else None,
		ai_prompt_version=explanation.prompt_version if explanation else None,
		replay_artifact_path=replay_artifact_path,
		complete=not missing,
		missing_fields=missing,
	)


def is_actionable(transparency: TransparencyOut) -> Tuple[bool, List[str]]:
	"""UC-002 extension 2a: incomplete transparency makes a finding non-actionable.

	Returns the decision and the reasons, so the caller can explain the refusal rather
	than just rejecting it.
	"""
	return transparency.complete, list(transparency.missing_fields)
