from __future__ import annotations

"""Rule packs and resolution queues.

Rule packs are read-only here: authoring and publishing them is UC-004, which belongs
to the audit-engine module. The API only resolves the published version so a run can
record which rules produced its findings.
"""

from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from module_4_api_ui.backend.constants import (
	RULE_PACK_PUBLISHED,
	TERMINAL_STATUSES,
)
from shared.database.models import (
	FindingAssignmentRow,
	FindingRow,
	ResolutionQueueRow,
	RulePackRow,
)


GOVERNANCE_QUEUE_NAME = "governance-escalation"


def list_rule_packs(session: Session) -> List[RulePackRow]:
	statement = select(RulePackRow).order_by(RulePackRow.id.desc())
	return list(session.execute(statement).scalars().all())


def get_rule_pack_by_version(session: Session, version: str) -> RulePackRow | None:
	statement = select(RulePackRow).where(RulePackRow.version == version)
	return session.execute(statement).scalar_one_or_none()


def get_published_rule_pack(session: Session) -> RulePackRow | None:
	"""Most recently published pack, used when a run does not name a version."""
	statement = (
		select(RulePackRow)
		.where(RulePackRow.status == RULE_PACK_PUBLISHED)
		.order_by(RulePackRow.published_at.desc().nullslast(), RulePackRow.id.desc())
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def list_queues(session: Session) -> List[ResolutionQueueRow]:
	statement = select(ResolutionQueueRow).order_by(ResolutionQueueRow.id)
	return list(session.execute(statement).scalars().all())


def get_queue(session: Session, queue_id: int) -> ResolutionQueueRow | None:
	return session.get(ResolutionQueueRow, queue_id)


def get_queue_by_name(session: Session, name: str) -> ResolutionQueueRow | None:
	statement = select(ResolutionQueueRow).where(ResolutionQueueRow.name == name)
	return session.execute(statement).scalar_one_or_none()


def get_governance_queue(session: Session) -> ResolutionQueueRow | None:
	"""Fallback queue for findings with no owner mapping (UC-003 extension 4a)."""
	queue = get_queue_by_name(session, GOVERNANCE_QUEUE_NAME)
	if queue is not None:
		return queue
	statement = (
		select(ResolutionQueueRow)
		.where(ResolutionQueueRow.owner_type == "compliance")
		.order_by(ResolutionQueueRow.id)
		.limit(1)
	)
	return session.execute(statement).scalar_one_or_none()


def open_counts_by_queue(session: Session) -> Dict[int, int]:
	"""Number of findings per queue that have not reached a terminal status."""
	statement = (
		select(FindingAssignmentRow.queue_id, func.count(func.distinct(FindingRow.id)))
		.join(FindingRow, FindingAssignmentRow.finding_id == FindingRow.id)
		.where(FindingRow.status.notin_(tuple(TERMINAL_STATUSES)))
		.group_by(FindingAssignmentRow.queue_id)
	)
	return {int(row[0]): int(row[1]) for row in session.execute(statement).all()}
