from __future__ import annotations

"""Audit run triggering and status (UC-001)."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session, sessionmaker

from module_4_api_ui.backend.dependencies import (
	get_audit_engine,
	get_job_registry,
	get_principal,
	get_session,
	get_session_factory,
	require_roles,
)
from module_4_api_ui.backend.schemas.catalog import (
	AuditRunCreateRequest,
	AuditRunDetailOut,
	AuditRunOut,
)
from module_4_api_ui.backend.schemas.common import Page
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.audit_run_service import AuditRunService


router = APIRouter(prefix="/audit-runs", tags=["audit-runs"])


def _service(
	session_factory: "sessionmaker[Session]" = Depends(get_session_factory),
	engine=Depends(get_audit_engine),
	jobs=Depends(get_job_registry),
) -> AuditRunService:
	return AuditRunService(session_factory, engine, jobs)


@router.post("", response_model=AuditRunOut, status_code=status.HTTP_202_ACCEPTED)
def create_audit_run(
	payload: AuditRunCreateRequest,
	background_tasks: BackgroundTasks,
	session: Session = Depends(get_session),
	service: AuditRunService = Depends(_service),
	principal: Principal = Depends(require_roles("steward", "analyst")),
) -> AuditRunOut:
	"""Queue a run and return immediately; the client polls for completion."""
	run = service.create_run(session, payload.batch_id, payload.rule_pack_version)
	background_tasks.add_task(service.execute, run.id)
	return run


@router.get("", response_model=Page[AuditRunOut])
def list_audit_runs(
	batch_id: int | None = Query(default=None),
	run_status: str | None = Query(default=None, alias="status"),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=25, ge=1, le=200),
	session: Session = Depends(get_session),
	service: AuditRunService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> Page[AuditRunOut]:
	items, total = service.list_runs(
		session, batch_id=batch_id, status=run_status, page=page, page_size=page_size
	)
	return Page.build(items, total, page, page_size)


@router.get("/{run_id}", response_model=AuditRunDetailOut)
def read_audit_run(
	run_id: int,
	session: Session = Depends(get_session),
	service: AuditRunService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> AuditRunDetailOut:
	return service.detail(session, run_id)
