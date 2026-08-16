from __future__ import annotations

"""Finding queue, detail, and triage (UC-002)."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from module_4_api_ui.backend.dependencies import get_principal, get_session, require_roles
from module_4_api_ui.backend.schemas.common import Page
from module_4_api_ui.backend.schemas.findings import (
	FindingDetailOut,
	FindingEvidenceOut,
	FindingStatsOut,
	FindingSummaryOut,
	StatusHistoryOut,
	StatusTransitionRequest,
	TriageRequest,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.finding_service import FindingService


router = APIRouter(prefix="/findings", tags=["findings"])


def _service() -> FindingService:
	return FindingService()


@router.get("", response_model=Page[FindingSummaryOut])
def list_findings(
	audit_run_id: int | None = Query(default=None),
	batch_id: int | None = Query(default=None),
	status: List[str] | None = Query(default=None),
	severity: List[str] | None = Query(default=None),
	priority: List[str] | None = Query(default=None),
	finding_type: List[str] | None = Query(default=None),
	rule_id: str | None = Query(default=None),
	queue_id: int | None = Query(default=None),
	open_only: bool = Query(default=False),
	search: str | None = Query(default=None),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=25, ge=1, le=200),
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> Page[FindingSummaryOut]:
	"""Prioritised finding queue — ordered by priority, then severity, then recency."""
	items, total = service.list_findings(
		session,
		filters={
			"audit_run_id": audit_run_id,
			"batch_id": batch_id,
			"statuses": status,
			"severities": severity,
			"priorities": priority,
			"finding_types": finding_type,
			"rule_id": rule_id,
			"queue_id": queue_id,
			"open_only": open_only,
			"search": search,
		},
		page=page,
		page_size=page_size,
	)
	return Page.build(items, total, page, page_size)


@router.get("/stats", response_model=FindingStatsOut)
def read_finding_stats(
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> FindingStatsOut:
	return service.stats(session)


@router.get("/{finding_id}", response_model=FindingDetailOut)
def read_finding(
	finding_id: int,
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> FindingDetailOut:
	return service.detail(session, finding_id, principal)


@router.get("/{finding_id}/evidence", response_model=List[FindingEvidenceOut])
def read_finding_evidence(
	finding_id: int,
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> List[FindingEvidenceOut]:
	return service.evidence(session, finding_id)


@router.get("/{finding_id}/history", response_model=List[StatusHistoryOut])
def read_finding_history(
	finding_id: int,
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> List[StatusHistoryOut]:
	return service.history(session, finding_id)


@router.post("/{finding_id}/triage", response_model=FindingDetailOut)
def triage_finding(
	finding_id: int,
	payload: TriageRequest,
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(require_roles("steward", "analyst")),
) -> FindingDetailOut:
	return service.triage(session, finding_id, payload.disposition, payload.notes, principal)


@router.post("/{finding_id}/status", response_model=FindingDetailOut)
def transition_finding(
	finding_id: int,
	payload: StatusTransitionRequest,
	session: Session = Depends(get_session),
	service: FindingService = Depends(_service),
	principal: Principal = Depends(require_roles("steward", "analyst", "compliance")),
) -> FindingDetailOut:
	return service.transition(session, finding_id, payload.to_status, payload.notes, principal)
