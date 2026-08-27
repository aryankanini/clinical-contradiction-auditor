from __future__ import annotations

"""Resolution approval and owner assignment (UC-003)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from module_4_api_ui.backend.dependencies import get_principal, get_session, require_roles
from module_4_api_ui.backend.schemas.resolution import (
	AssignmentOut,
	AssignmentRequest,
	ResolutionApprovalRequest,
	ResolutionOut,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.resolution_service import ResolutionService


router = APIRouter(tags=["resolution"])


def _service() -> ResolutionService:
	return ResolutionService()


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
