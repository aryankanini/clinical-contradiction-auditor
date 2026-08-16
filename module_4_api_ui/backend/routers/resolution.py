from __future__ import annotations

"""Resolution approval and owner assignment (UC-003)."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from module_4_api_ui.backend.dependencies import get_principal, get_session, require_roles
from module_4_api_ui.backend.errors import NotFoundError
from module_4_api_ui.backend.repositories import catalog_repository, finding_repository
from module_4_api_ui.backend.schemas.common import Page
from module_4_api_ui.backend.schemas.findings import FindingSummaryOut
from module_4_api_ui.backend.schemas.resolution import (
	AssignmentOut,
	AssignmentRequest,
	ResolutionApprovalRequest,
	ResolutionOut,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.finding_service import FindingService
from module_4_api_ui.backend.services.resolution_service import ResolutionService


router = APIRouter(tags=["resolution"])


def _service() -> ResolutionService:
	return ResolutionService()


@router.get("/findings/{finding_id}/resolution/draft")
def read_resolution_draft(
	finding_id: int,
	session: Session = Depends(get_session),
	service: ResolutionService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> Dict[str, Any] | None:
	"""The AI's proposed action. Advisory only — approval is a separate, human step."""
	return service.draft(session, finding_id)


@router.get("/findings/{finding_id}/resolution", response_model=ResolutionOut | None)
def read_resolution(
	finding_id: int,
	session: Session = Depends(get_session),
	service: ResolutionService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> ResolutionOut | None:
	return service.read(session, finding_id)


@router.put("/findings/{finding_id}/resolution", response_model=ResolutionOut)
def approve_resolution(
	finding_id: int,
	payload: ResolutionApprovalRequest,
	session: Session = Depends(get_session),
	service: ResolutionService = Depends(_service),
	principal: Principal = Depends(require_roles("steward")),
) -> ResolutionOut:
	return service.approve(session, finding_id, payload, principal)


@router.post("/findings/{finding_id}/assignment", response_model=AssignmentOut)
def assign_finding(
	finding_id: int,
	payload: AssignmentRequest,
	session: Session = Depends(get_session),
	service: ResolutionService = Depends(_service),
	principal: Principal = Depends(require_roles("steward")),
) -> AssignmentOut:
	return service.assign(session, finding_id, payload.queue_id, payload.assigned_to, principal)


@router.get("/queues/{queue_id}/findings", response_model=Page[FindingSummaryOut])
def list_queue_findings(
	queue_id: int,
	page: int = 1,
	page_size: int = 25,
	session: Session = Depends(get_session),
	principal: Principal = Depends(get_principal),
) -> Page[FindingSummaryOut]:
	if catalog_repository.get_queue(session, queue_id) is None:
		raise NotFoundError(f"Resolution queue {queue_id} was not found.")

	finding_service = FindingService()
	items, total = finding_service.list_findings(
		session,
		filters={
			"audit_run_id": None,
			"batch_id": None,
			"statuses": None,
			"severities": None,
			"priorities": None,
			"finding_types": None,
			"rule_id": None,
			"queue_id": queue_id,
			"open_only": False,
			"search": None,
		},
		page=page,
		page_size=page_size,
	)
	return Page.build(items, total, page, page_size)
