from __future__ import annotations

"""Finding review, triage, and lifecycle (UC-002, FR-006/FR-008/FR-010)."""

import json
from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy.orm import Session

from module_4_api_ui.backend.constants import (
	STATUS_ACCEPTED,
	STATUS_NON_ACTIONABLE,
	SYSTEM_ACTOR,
	TERMINAL_STATUSES,
	TRIAGE_TARGET_STATUS,
)
from module_4_api_ui.backend.errors import ConflictError, NotFoundError
from module_4_api_ui.backend.repositories import batch_repository, finding_repository
from module_4_api_ui.backend.schemas.explanations import (
	AIExplanationOut,
	EvidenceSynthesisOut,
	ResolutionDraftOut,
)
from module_4_api_ui.backend.schemas.findings import (
	FindingDetailOut,
	FindingEvidenceOut,
	FindingStatsOut,
	FindingSummaryOut,
	StatusHistoryOut,
)
from module_4_api_ui.backend.schemas.resolution import AssignmentOut, ResolutionOut
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services import status_machine, transparency
from shared.database.models import AIExplanationRow, FindingRow


def _confidence_payload(explanation: AIExplanationRow | None) -> Dict[str, Any]:
	if explanation is None:
		return {}
	raw = explanation.confidence_json
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except ValueError:
			return {}
	return raw if isinstance(raw, dict) else {}


def explanation_out(explanation: AIExplanationRow | None) -> AIExplanationOut | None:
	if explanation is None:
		return None

	payload = _confidence_payload(explanation)
	evidence = payload.get("evidence")
	draft = payload.get("resolution_draft")
	confidence_context = str(payload.get("confidence_context") or "")

	return AIExplanationOut(
		id=explanation.id,
		finding_id=explanation.finding_id,
		model_name=explanation.model_name,
		prompt_version=explanation.prompt_version,
		rationale_text=explanation.rationale_text,
		confidence_context=confidence_context,
		evidence=EvidenceSynthesisOut(**evidence) if isinstance(evidence, dict) else None,
		resolution_draft=ResolutionDraftOut(**draft) if isinstance(draft, dict) else None,
		created_at=explanation.created_at,
		# Module 3 parses the model's reply by splitting on literal markers; an empty
		# confidence context means that parse degraded, which UC-003 extension 2a treats
		# as low confidence requiring manual resolution entry.
		low_confidence=not confidence_context.strip(),
	)


class FindingService:
	def triage(
		self,
		session: Session,
		finding_id: int,
		disposition: str,
		notes: str | None,
		principal: Principal,
	) -> FindingDetailOut:
		"""Apply a triage disposition (UC-002 step 4).

		``accept`` is refused when the finding's transparency payload is incomplete —
		UC-002 extension 2a requires such findings be treated as non-actionable and
		routed for data-quality remediation instead.
		"""
		finding = self._require_finding(session, finding_id)
		target = TRIAGE_TARGET_STATUS.get(disposition)
		if target is None:
			raise ConflictError(
				f"Unknown triage disposition '{disposition}'.",
				context={"allowed": sorted(TRIAGE_TARGET_STATUS)},
			)

		if target == STATUS_ACCEPTED:
			payload = self._transparency_for(session, finding)
			actionable, missing = transparency.is_actionable(payload)
			if not actionable:
				raise ConflictError(
					"Finding cannot be accepted while its transparency fields are incomplete.",
					code="transparency_incomplete",
					context={"missing_fields": missing},
				)

		has_resolution = finding_repository.get_approved_resolution(session, finding_id) is not None
		has_assignment = finding_repository.get_active_assignment(session, finding_id) is not None

		for step in status_machine.path_from(finding.status, target):
			status_machine.assert_transition_allowed(
				finding.status,
				step,
				principal.role,
				has_approved_resolution=has_resolution,
				has_assignment=has_assignment,
			)
			finding_repository.record_transition(
				session,
				finding,
				step,
				principal.user_id,
				notes if step == target else "Opened for review.",
			)

		session.commit()
		return self.detail(session, finding_id, principal)

	def transition(
		self,
		session: Session,
		finding_id: int,
		to_status: str,
		notes: str | None,
		principal: Principal,
	) -> FindingDetailOut:
		finding = self._require_finding(session, finding_id)
		has_resolution = finding_repository.get_approved_resolution(session, finding_id) is not None
		has_assignment = finding_repository.get_active_assignment(session, finding_id) is not None

		status_machine.assert_transition_allowed(
			finding.status,
			to_status,
			principal.role,
			has_approved_resolution=has_resolution,
			has_assignment=has_assignment,
		)
		finding_repository.record_transition(session, finding, to_status, principal.user_id, notes)
		session.commit()
		return self.detail(session, finding_id, principal)

	def mark_non_actionable(
		self,
		session: Session,
		finding_id: int,
		reason: str,
		principal: Principal,
	) -> FindingDetailOut:
		return self.transition(session, finding_id, STATUS_NON_ACTIONABLE, reason, principal)

	# --- reads ----------------------------------------------------------

	def list_findings(
		self,
		session: Session,
		*,
		filters: Dict[str, Any],
		page: int,
		page_size: int,
	) -> Tuple[List[FindingSummaryOut], int]:
		rows, total = finding_repository.list_findings(
			session, page=page, page_size=page_size, **filters
		)
		return [self._summary(session, row) for row in rows], total

	def detail(
		self,
		session: Session,
		finding_id: int,
		principal: Principal,
	) -> FindingDetailOut:
		finding = finding_repository.get_finding_with_relations(session, finding_id)
		if finding is None:
			raise NotFoundError(f"Finding {finding_id} was not found.")

		explanation = finding_repository.latest_explanation(session, finding_id)
		payload = self._transparency_for(session, finding, explanation)
		resolution_row = finding_repository.get_approved_resolution(session, finding_id)
		assignment_row = finding_repository.get_active_assignment(session, finding_id)

		summary = self._summary(session, finding, explanation=explanation, transparency_payload=payload)

		return FindingDetailOut(
			**summary.model_dump(),
			transparency=payload,
			evidence=[
				self._evidence_out(item) for item in finding_repository.engine_evidence(finding)
			],
			explanation=explanation_out(explanation),
			resolution=self._resolution_out(resolution_row),
			assignment=self._assignment_out(assignment_row),
			status_history=[
				StatusHistoryOut.model_validate(row)
				for row in finding_repository.list_status_history(session, finding_id)
			],
			allowed_transitions=status_machine.allowed_transitions_for(
				finding.status,
				principal.role,
				has_approved_resolution=resolution_row is not None,
				has_assignment=assignment_row is not None,
			),
		)

	def stats(self, session: Session) -> FindingStatsOut:
		by_status = finding_repository.count_by_column(session, FindingRow.status)
		total = sum(by_status.values())
		open_total = sum(
			count for status, count in by_status.items() if status not in TERMINAL_STATUSES
		)
		return FindingStatsOut(
			total=total,
			open_total=open_total,
			by_status=by_status,
			by_severity=finding_repository.count_by_column(session, FindingRow.severity),
			by_priority=finding_repository.count_by_column(session, FindingRow.priority),
			by_finding_type=finding_repository.count_by_column(session, FindingRow.finding_type),
		)

	# --- helpers --------------------------------------------------------

	@staticmethod
	def _require_finding(session: Session, finding_id: int) -> FindingRow:
		finding = finding_repository.get_finding(session, finding_id)
		if finding is None:
			raise NotFoundError(f"Finding {finding_id} was not found.")
		return finding

	@staticmethod
	def _replay_path(session: Session, finding: FindingRow) -> str | None:
		run = finding.audit_run
		if run is None:
			return None
		batch = batch_repository.get_batch(session, run.batch_id)
		return batch.replay_artifact_path if batch else None

	def _transparency_for(
		self,
		session: Session,
		finding: FindingRow,
		explanation: AIExplanationRow | None = None,
	):
		if explanation is None:
			explanation = finding_repository.latest_explanation(session, finding.id)
		run = finding.audit_run
		return transparency.build_transparency(
			finding,
			explanation,
			rule_pack_version=run.rule_pack.version if run and run.rule_pack else None,
			replay_artifact_path=self._replay_path(session, finding),
		)

	def _summary(
		self,
		session: Session,
		finding: FindingRow,
		explanation: AIExplanationRow | None = None,
		transparency_payload=None,
	) -> FindingSummaryOut:
		if transparency_payload is None:
			transparency_payload = self._transparency_for(session, finding, explanation)

		assignment = finding.assignments[-1] if finding.assignments else None
		return FindingSummaryOut(
			id=finding.id,
			audit_run_id=finding.audit_run_id,
			rule_id=finding.rule_id,
			finding_type=finding.finding_type,
			severity=finding.severity,
			priority=finding.priority,
			status=finding.status,
			summary=finding.summary,
			audit_outcome=finding.audit_outcome,
			created_at=finding.created_at,
			evidence_count=len(finding_repository.engine_evidence(finding)),
			has_explanation=bool(finding.ai_explanations),
			transparency_complete=transparency_payload.complete,
			assigned_queue_name=assignment.queue.name if assignment and assignment.queue else None,
			assigned_to=assignment.assigned_to if assignment else None,
		)

	@staticmethod
	def _evidence_out(item) -> FindingEvidenceOut:
		resource = item.normalized_resource
		payload = dict(item.evidence_payload or {})
		return FindingEvidenceOut(
			id=item.id,
			evidence_type=item.evidence_type,
			normalized_resource_id=item.normalized_resource_id,
			record_external_id=resource.record_external_id
			if resource
			else payload.get("record_id"),
			resource_type=resource.resource_type if resource else payload.get("resource_type"),
			status_value=resource.status_value if resource else payload.get("status"),
			status_state=resource.status_state if resource else payload.get("status_state"),
			primary_timestamp=resource.primary_timestamp if resource else None,
			evidence_payload=payload,
		)

	@staticmethod
	def _resolution_out(row) -> ResolutionOut | None:
		if row is None:
			return None
		payload = dict(row.evidence_payload or {})
		return ResolutionOut(
			evidence_id=row.id,
			suggested_action=payload.get("suggested_action", ""),
			rationale=payload.get("rationale", ""),
			source=payload.get("source", "manual"),
			approved_by=payload.get("approved_by", SYSTEM_ACTOR),
			approved_at=payload.get("approved_at"),
			notes=payload.get("notes"),
		)

	@staticmethod
	def _assignment_out(row) -> AssignmentOut | None:
		if row is None or row.queue is None:
			return None
		return AssignmentOut(
			id=row.id,
			queue_id=row.queue_id,
			queue_name=row.queue.name,
			owner_type=row.queue.owner_type,
			assigned_to=row.assigned_to,
			assigned_at=row.assigned_at,
		)
