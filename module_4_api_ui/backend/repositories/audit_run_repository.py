from __future__ import annotations

"""Audit run lifecycle and bulk finding persistence."""

from datetime import datetime, timezone
from typing import Dict, List, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from module_4_api_ui.backend.constants import (
	ACTIVE_RUN_STATUSES,
	RUN_QUEUED,
	STATUS_NEW,
	SYSTEM_ACTOR,
)
from shared.database.models import (
	AuditRunRow,
	FindingEvidenceRow,
	FindingRow,
	FindingStatusHistoryRow,
	NormalizedResourceRow,
)
from shared.models.audit_finding import DetectedFinding


def get_run(session: Session, run_id: int) -> AuditRunRow | None:
	statement = (
		select(AuditRunRow)
		.where(AuditRunRow.id == run_id)
		.options(selectinload(AuditRunRow.rule_pack), selectinload(AuditRunRow.batch))
	)
	return session.execute(statement).scalar_one_or_none()


def list_runs(
	session: Session,
	*,
	batch_id: int | None = None,
	status: str | None = None,
	page: int = 1,
	page_size: int = 25,
) -> Tuple[List[AuditRunRow], int]:
	filters = []
	if batch_id is not None:
		filters.append(AuditRunRow.batch_id == batch_id)
	if status:
		filters.append(AuditRunRow.status == status)

	total = session.execute(
		select(func.count()).select_from(AuditRunRow).where(*filters)
	).scalar_one()

	statement = (
		select(AuditRunRow)
		.where(*filters)
		.options(selectinload(AuditRunRow.rule_pack), selectinload(AuditRunRow.batch))
		.order_by(AuditRunRow.started_at.desc(), AuditRunRow.id.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
	)
	return list(session.execute(statement).scalars().all()), int(total)


def has_active_run(session: Session, batch_id: int) -> bool:
	statement = (
		select(func.count())
		.select_from(AuditRunRow)
		.where(
			AuditRunRow.batch_id == batch_id,
			AuditRunRow.status.in_(tuple(ACTIVE_RUN_STATUSES)),
		)
	)
	return int(session.execute(statement).scalar_one()) > 0


def create_run(session: Session, batch_id: int, rule_pack_id: int) -> AuditRunRow:
	row = AuditRunRow(batch_id=batch_id, rule_pack_id=rule_pack_id, status=RUN_QUEUED)
	session.add(row)
	session.flush()
	return row


def set_run_status(
	session: Session,
	run: AuditRunRow,
	status: str,
	*,
	completed: bool = False,
) -> AuditRunRow:
	run.status = status
	if completed:
		run.completed_at = datetime.now(timezone.utc)
	session.add(run)
	return run


def fail_orphaned_runs(session: Session) -> int:
	"""Mark runs left mid-flight by a process restart as failed.

	Background execution is in-process, so a crash or reload would otherwise leave a run
	stuck in ``queued``/``running`` forever with no way to retry it.
	"""
	statement = select(AuditRunRow).where(AuditRunRow.status.in_(tuple(ACTIVE_RUN_STATUSES)))
	rows = list(session.execute(statement).scalars().all())
	for row in rows:
		row.status = "failed"
		row.completed_at = datetime.now(timezone.utc)
		session.add(row)
	return len(rows)


def persist_findings(
	session: Session,
	run: AuditRunRow,
	findings: Sequence[DetectedFinding],
	resource_ids_by_external_id: Dict[str, int],
) -> List[FindingRow]:
	"""Write engine output plus each finding's genesis history row.

	The genesis row (``None -> new``) is what gives every finding an unbroken audit
	trail from the moment it was detected.
	"""
	created: List[FindingRow] = []

	for detected in findings:
		finding = FindingRow(
			audit_run_id=run.id,
			rule_id=detected.rule_id,
			severity=detected.severity,
			priority=detected.priority,
			finding_type=detected.finding_type,
			status=STATUS_NEW,
			summary=detected.summary,
			audit_outcome=detected.audit_outcome,
		)
		session.add(finding)
		session.flush()

		for evidence in detected.evidence:
			resource_id = evidence.normalized_resource_id
			if resource_id is None and evidence.record_external_id:
				resource_id = resource_ids_by_external_id.get(evidence.record_external_id)
			session.add(
				FindingEvidenceRow(
					finding_id=finding.id,
					normalized_resource_id=resource_id,
					evidence_type=evidence.evidence_type,
					evidence_payload=dict(evidence.payload),
				)
			)

		session.add(
			FindingStatusHistoryRow(
				finding_id=finding.id,
				from_status=None,
				to_status=STATUS_NEW,
				changed_by=SYSTEM_ACTOR,
				notes=f"Detected by rule pack {run.rule_pack.version if run.rule_pack else '?'}.",
			)
		)
		created.append(finding)

	return created


def normalized_resource_ids(session: Session, batch_id: int) -> Dict[str, int]:
	statement = select(
		NormalizedResourceRow.record_external_id, NormalizedResourceRow.id
	).where(NormalizedResourceRow.batch_id == batch_id)
	return {row[0]: int(row[1]) for row in session.execute(statement).all()}


def count_findings(session: Session, run_id: int) -> int:
	statement = select(func.count()).select_from(FindingRow).where(FindingRow.audit_run_id == run_id)
	return int(session.execute(statement).scalar_one())
