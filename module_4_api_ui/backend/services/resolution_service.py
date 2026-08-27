from __future__ import annotations

"""Resolution approval and owner routing (UC-003, FR-009, FR-010)."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from module_4_api_ui.backend.constants import (
	EVIDENCE_APPROVED_RESOLUTION,
	STATUS_ESCALATED,
)
from module_4_api_ui.backend.errors import ConflictError, NotFoundError, ValidationError
from module_4_api_ui.backend.repositories import catalog_repository, finding_repository
from module_4_api_ui.backend.schemas.resolution import (
	AssignmentOut,
	ResolutionApprovalRequest,
	ResolutionOut,
)
from module_4_api_ui.backend.security import Principal
from shared.database.models import FindingRow, ResolutionQueueRow


logger = logging.getLogger("clinical_auditor.api.resolution")


class ResolutionService:
	def approve(
		self,
		session: Session,
		finding_id: int,
		payload: ResolutionApprovalRequest,
		principal: Principal,
	) -> ResolutionOut:
		"""Record a human decision on a resolution (FR-009).

		Approving an ``ai`` resolution requires an explanation to exist, and a draft the
		model produced with low confidence cannot be rubber-stamped — UC-003 extension 2a
		requires manual entry in that case.
		"""
		finding = self._require_finding(session, finding_id)

		if payload.source == "ai":
			explanation = finding_repository.latest_explanation(session, finding_id)
			if explanation is None:
				raise ValidationError(
					"No AI draft exists for this finding; enter the resolution manually.",
					code="ai_draft_unavailable",
				)
			draft = self._draft_from(explanation)
			if draft.get("low_confidence"):
				raise ValidationError(
					"The AI draft is low confidence and must be edited or written manually.",
					code="ai_draft_low_confidence",
					context={"source_required": ["ai_edited", "manual"]},
				)

		row = finding_repository.add_evidence(
			session,
			finding_id,
			EVIDENCE_APPROVED_RESOLUTION,
			{
				"suggested_action": payload.suggested_action,
				"rationale": payload.rationale,
				"source": payload.source,
				"approved_by": principal.user_id,
				"approved_at": datetime.now(timezone.utc).isoformat(),
				"notes": payload.notes,
			},
		)
		session.flush()
		session.commit()
		session.refresh(row)

		logger.info(
			"Resolution approved for finding %s by %s (source=%s)",
			finding_id,
			principal.user_id,
			payload.source,
		)
		return self._resolution_out(row)

	def assign(
		self,
		session: Session,
		finding_id: int,
		queue_id: int | None,
		assigned_to: str | None,
		principal: Principal,
	) -> AssignmentOut:
		"""Route a finding to an owner queue (FR-010).

		With no queue given, routing is derived from each queue's ``config_json``. When
		nothing matches the finding goes to the governance queue and is escalated, which
		is UC-003 extension 4a.
		"""
		finding = self._require_finding(session, finding_id)

		auto_routed = False
		escalated = False

		if queue_id is not None:
			queue = catalog_repository.get_queue(session, queue_id)
			if queue is None:
				raise NotFoundError(f"Resolution queue {queue_id} was not found.")
		else:
			queue = self._route(session, finding)
			auto_routed = True
			if queue is None:
				queue = catalog_repository.get_governance_queue(session)
				escalated = True
				if queue is None:
					raise ConflictError(
						"No resolution queue is configured to own this finding.",
						code="no_owner_queue",
					)

		row = finding_repository.assign_to_queue(session, finding_id, queue, assigned_to)

		if escalated and finding.status != STATUS_ESCALATED:
			from module_4_api_ui.backend.services import status_machine

			if STATUS_ESCALATED in status_machine.legal_targets(finding.status):
				finding_repository.record_transition(
					session,
					finding,
					STATUS_ESCALATED,
					principal.user_id,
					"No owner mapping matched; escalated to governance.",
				)

		session.flush()
		session.commit()
		session.refresh(row)

		return AssignmentOut(
			id=row.id,
			queue_id=row.queue_id,
			queue_name=queue.name,
			owner_type=queue.owner_type,
			assigned_to=row.assigned_to,
			assigned_at=row.assigned_at,
			auto_routed=auto_routed,
			escalated=escalated,
		)

	# --- helpers --------------------------------------------------------

	@staticmethod
	def _route(session: Session, finding: FindingRow) -> ResolutionQueueRow | None:
		for queue in catalog_repository.list_queues(session):
			config = queue.config_json or {}
			routing = config.get("routing") or {}
			if not routing:
				continue
			types = routing.get("finding_type") or []
			severities = routing.get("severity") or []
			if types and finding.finding_type in types:
				return queue
			if severities and finding.severity in severities:
				return queue
		return None

	@staticmethod
	def _draft_from(explanation) -> Dict[str, Any]:
		raw = explanation.confidence_json
		if isinstance(raw, str):
			try:
				raw = json.loads(raw)
			except ValueError:
				return {}
		if not isinstance(raw, dict):
			return {}
		draft = raw.get("resolution_draft")
		return draft if isinstance(draft, dict) else {}

	@staticmethod
	def _require_finding(session: Session, finding_id: int) -> FindingRow:
		finding = finding_repository.get_finding(session, finding_id)
		if finding is None:
			raise NotFoundError(f"Finding {finding_id} was not found.")
		return finding

	@staticmethod
	def _resolution_out(row) -> ResolutionOut:
		payload = dict(row.evidence_payload or {})
		return ResolutionOut(
			evidence_id=row.id,
			suggested_action=payload.get("suggested_action", ""),
			rationale=payload.get("rationale", ""),
			source=payload.get("source", "manual"),
			approved_by=payload.get("approved_by", ""),
			approved_at=payload.get("approved_at"),
			notes=payload.get("notes"),
		)
