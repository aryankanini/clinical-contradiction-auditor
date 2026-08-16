from __future__ import annotations

"""Finding, evidence, assignment, and status-history persistence."""

from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from module_4_api_ui.backend.constants import (
	ENGINE_EVIDENCE_TYPES,
	EVIDENCE_APPROVED_RESOLUTION,
	PRIORITY_RANK,
	SEVERITY_RANK,
	TERMINAL_STATUSES,
)
from shared.database.models import (
	AIExplanationRow,
	AuditRunRow,
	FindingAssignmentRow,
	FindingEvidenceRow,
	FindingRow,
	FindingStatusHistoryRow,
	ResolutionQueueRow,
)


_SEVERITY_ORDER = case(SEVERITY_RANK, value=FindingRow.severity, else_=0)
_PRIORITY_ORDER = case(PRIORITY_RANK, value=FindingRow.priority, else_=99)


def get_finding(session: Session, finding_id: int) -> FindingRow | None:
	return session.get(FindingRow, finding_id)


def get_finding_with_relations(session: Session, finding_id: int) -> FindingRow | None:
	statement = (
		select(FindingRow)
		.where(FindingRow.id == finding_id)
		.options(
			selectinload(FindingRow.evidence_items).selectinload(
				FindingEvidenceRow.normalized_resource
			),
			selectinload(FindingRow.status_history),
			selectinload(FindingRow.assignments).selectinload(FindingAssignmentRow.queue),
			selectinload(FindingRow.ai_explanations),
			selectinload(FindingRow.audit_run).selectinload(AuditRunRow.rule_pack),
		)
	)
	return session.execute(statement).scalar_one_or_none()


def list_findings(
	session: Session,
	*,
	audit_run_id: int | None = None,
	batch_id: int | None = None,
	statuses: Sequence[str] | None = None,
	severities: Sequence[str] | None = None,
	priorities: Sequence[str] | None = None,
	finding_types: Sequence[str] | None = None,
	rule_id: str | None = None,
	queue_id: int | None = None,
	open_only: bool = False,
	search: str | None = None,
	page: int = 1,
	page_size: int = 25,
) -> Tuple[List[FindingRow], int]:
	"""Prioritised, filtered finding queue (UC-002 step 1).

	Default ordering is priority first, then severity, then most recent — the order a
	steward should work the queue in.
	"""
	filters = []
	if audit_run_id is not None:
		filters.append(FindingRow.audit_run_id == audit_run_id)
	if statuses:
		filters.append(FindingRow.status.in_(list(statuses)))
	if severities:
		filters.append(FindingRow.severity.in_(list(severities)))
	if priorities:
		filters.append(FindingRow.priority.in_(list(priorities)))
	if finding_types:
		filters.append(FindingRow.finding_type.in_(list(finding_types)))
	if rule_id:
		filters.append(FindingRow.rule_id == rule_id)
	if open_only:
		filters.append(FindingRow.status.notin_(tuple(TERMINAL_STATUSES)))
	if search:
		filters.append(FindingRow.summary.ilike(f"%{search}%"))

	statement = select(FindingRow)
	count_statement = select(func.count(func.distinct(FindingRow.id))).select_from(FindingRow)

	if batch_id is not None:
		statement = statement.join(AuditRunRow, FindingRow.audit_run_id == AuditRunRow.id)
		count_statement = count_statement.join(
			AuditRunRow, FindingRow.audit_run_id == AuditRunRow.id
		)
		filters.append(AuditRunRow.batch_id == batch_id)

	if queue_id is not None:
		statement = statement.join(
			FindingAssignmentRow, FindingAssignmentRow.finding_id == FindingRow.id
		)
		count_statement = count_statement.join(
			FindingAssignmentRow, FindingAssignmentRow.finding_id == FindingRow.id
		)
		filters.append(FindingAssignmentRow.queue_id == queue_id)

	statement = statement.where(*filters)
	count_statement = count_statement.where(*filters)

	total = session.execute(count_statement).scalar_one()

	statement = (
		statement.options(
			selectinload(FindingRow.evidence_items),
			selectinload(FindingRow.ai_explanations),
			selectinload(FindingRow.assignments).selectinload(FindingAssignmentRow.queue),
		)
		.order_by(_PRIORITY_ORDER.asc(), _SEVERITY_ORDER.desc(), FindingRow.created_at.desc(), FindingRow.id.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
		.distinct()
	)
	return list(session.execute(statement).scalars().all()), int(total)


def count_by_column(session: Session, column: Any, *, open_only: bool = False) -> Dict[str, int]:
	statement = select(column, func.count()).select_from(FindingRow)
	if open_only:
		statement = statement.where(FindingRow.status.notin_(tuple(TERMINAL_STATUSES)))
	statement = statement.group_by(column)
	return {str(row[0]): int(row[1]) for row in session.execute(statement).all()}


def counts_for_run(session: Session, audit_run_id: int, column: Any) -> Dict[str, int]:
	statement = (
		select(column, func.count())
		.select_from(FindingRow)
		.where(FindingRow.audit_run_id == audit_run_id)
		.group_by(column)
	)
	return {str(row[0]): int(row[1]) for row in session.execute(statement).all()}


def record_transition(
	session: Session,
	finding: FindingRow,
	to_status: str,
	changed_by: str,
	notes: str | None = None,
) -> FindingStatusHistoryRow:
	"""Move a finding and append the matching history row in one place.

	Every mutator routes through this, so ``findings.status`` and
	``finding_status_history`` cannot drift apart — that trail is what FR-012 relies on.
	"""
	from_status = finding.status
	finding.status = to_status
	row = FindingStatusHistoryRow(
		finding_id=finding.id,
		from_status=from_status,
		to_status=to_status,
		changed_by=changed_by,
		notes=notes,
	)
	session.add(row)
	return row


def list_status_history(session: Session, finding_id: int) -> List[FindingStatusHistoryRow]:
	statement = (
		select(FindingStatusHistoryRow)
		.where(FindingStatusHistoryRow.finding_id == finding_id)
		.order_by(FindingStatusHistoryRow.changed_at, FindingStatusHistoryRow.id)
	)
	return list(session.execute(statement).scalars().all())


def list_evidence(session: Session, finding_id: int) -> List[FindingEvidenceRow]:
	statement = (
		select(FindingEvidenceRow)
		.where(FindingEvidenceRow.finding_id == finding_id)
		.options(selectinload(FindingEvidenceRow.normalized_resource))
		.order_by(FindingEvidenceRow.id)
	)
	return list(session.execute(statement).scalars().all())


def engine_evidence(finding: FindingRow) -> List[FindingEvidenceRow]:
	"""Only the evidence the audit engine produced.

	``finding_evidence`` doubles as the store for approved resolutions and compliance
	sign-off, so the engine's own records have to be separated before display.
	"""
	return [item for item in finding.evidence_items if item.evidence_type in ENGINE_EVIDENCE_TYPES]


def get_approved_resolution(session: Session, finding_id: int) -> FindingEvidenceRow | None:
	statement = (
		select(FindingEvidenceRow)
		.where(
			FindingEvidenceRow.finding_id == finding_id,
			FindingEvidenceRow.evidence_type == EVIDENCE_APPROVED_RESOLUTION,
		)
		.order_by(FindingEvidenceRow.id.desc())
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def get_active_assignment(session: Session, finding_id: int) -> FindingAssignmentRow | None:
	statement = (
		select(FindingAssignmentRow)
		.where(FindingAssignmentRow.finding_id == finding_id)
		.options(selectinload(FindingAssignmentRow.queue))
		.order_by(FindingAssignmentRow.id.desc())
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def add_evidence(
	session: Session,
	finding_id: int,
	evidence_type: str,
	payload: Dict[str, Any],
	normalized_resource_id: int | None = None,
) -> FindingEvidenceRow:
	row = FindingEvidenceRow(
		finding_id=finding_id,
		normalized_resource_id=normalized_resource_id,
		evidence_type=evidence_type,
		evidence_payload=payload,
	)
	session.add(row)
	return row


def assign_to_queue(
	session: Session,
	finding_id: int,
	queue: ResolutionQueueRow,
	assigned_to: str | None,
) -> FindingAssignmentRow:
	row = FindingAssignmentRow(
		finding_id=finding_id,
		queue_id=queue.id,
		assigned_to=assigned_to,
	)
	session.add(row)
	return row


def latest_explanation(session: Session, finding_id: int) -> AIExplanationRow | None:
	"""Most recent explanation for a finding.

	``ai_explanations`` has no uniqueness constraint, so rows accumulate. The ``id``
	tiebreaker matters: ``created_at`` uses a per-statement ``func.now()``, so rows
	written in one transaction can share a timestamp.
	"""
	statement = (
		select(AIExplanationRow)
		.where(AIExplanationRow.finding_id == finding_id)
		.order_by(AIExplanationRow.created_at.desc(), AIExplanationRow.id.desc())
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def list_explanations(session: Session, finding_id: int) -> List[AIExplanationRow]:
	statement = (
		select(AIExplanationRow)
		.where(AIExplanationRow.finding_id == finding_id)
		.order_by(AIExplanationRow.created_at.desc(), AIExplanationRow.id.desc())
	)
	return list(session.execute(statement).scalars().all())
