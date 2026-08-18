from __future__ import annotations

"""AI explanation endpoints (FR-007).

These are ``async def`` — unlike the rest of the API — because
``AIReasoningOrchestrator.reason`` is genuinely awaitable and makes three sequential
Bedrock round-trips. Generation runs in the background so a slow provider never blocks
the findings queue.
"""

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.dependencies import (
	get_ai_orchestrator,
	get_config,
	get_job_registry,
	get_principal,
	get_session,
	get_session_factory,
	require_roles,
)
from module_4_api_ui.backend.errors import NotFoundError
from module_4_api_ui.backend.repositories import finding_repository
from module_4_api_ui.backend.schemas.explanations import (
	AIExplanationOut,
	ExplanationJobOut,
	ExplanationRequest,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.explanation_service import JOB_KIND, ExplanationService
from module_4_api_ui.backend.services.finding_service import explanation_out
from module_4_api_ui.backend.services.job_registry import JobRegistry


router = APIRouter(prefix="/findings", tags=["ai-explanations"])


def _service(
	session_factory: "sessionmaker[Session]" = Depends(get_session_factory),
	config: ApiConfig = Depends(get_config),
	orchestrator=Depends(get_ai_orchestrator),
	jobs: JobRegistry = Depends(get_job_registry),
) -> ExplanationService:
	return ExplanationService(session_factory, config, orchestrator, jobs)


@router.post("/{finding_id}/explanation", status_code=status.HTTP_202_ACCEPTED)
async def generate_explanation(
	finding_id: int,
	payload: ExplanationRequest,
	background_tasks: BackgroundTasks,
	response: Response,
	session: Session = Depends(get_session),
	service: ExplanationService = Depends(_service),
	jobs: JobRegistry = Depends(get_job_registry),
	principal: Principal = Depends(require_roles("steward", "analyst")),
):
	finding = await run_in_threadpool(finding_repository.get_finding, session, finding_id)
	if finding is None:
		raise NotFoundError(f"Finding {finding_id} was not found.")

	if not payload.force_refresh:
		cached = await run_in_threadpool(
			finding_repository.latest_explanation, session, finding_id
		)
		if cached is not None:
			response.status_code = status.HTTP_200_OK
			return explanation_out(cached)

	key = (JOB_KIND, finding_id)
	if not await jobs.claim(key):
		existing = await jobs.get(key)
		return ExplanationJobOut(
			finding_id=finding_id,
			state=existing.state if existing else "running",
			started_at=existing.started_at if existing else None,
		)

	background_tasks.add_task(service.generate, finding_id, principal.user_id)
	job = await jobs.get(key)
	return ExplanationJobOut(
		finding_id=finding_id,
		state=job.state if job else "pending",
		started_at=job.started_at if job else None,
	)


@router.get("/{finding_id}/explanation")
async def read_explanation(
	finding_id: int,
	response: Response,
	session: Session = Depends(get_session),
	jobs: JobRegistry = Depends(get_job_registry),
	principal: Principal = Depends(get_principal),
):
	cached = await run_in_threadpool(finding_repository.latest_explanation, session, finding_id)
	if cached is not None:
		return explanation_out(cached)

	job = await jobs.get((JOB_KIND, finding_id))
	if job is not None:
		return ExplanationJobOut(
			finding_id=finding_id,
			state=job.state,
			started_at=job.started_at,
			completed_at=job.completed_at,
			error=job.error,
		)

	response.status_code = status.HTTP_204_NO_CONTENT
	return None


@router.get("/{finding_id}/explanations", response_model=List[AIExplanationOut])
async def list_explanations(
	finding_id: int,
	session: Session = Depends(get_session),
	principal: Principal = Depends(get_principal),
) -> List[AIExplanationOut]:
	"""Every generated version, which FR-012 reproducibility review needs."""
	rows = await run_in_threadpool(finding_repository.list_explanations, session, finding_id)
	return [explanation_out(row) for row in rows if row is not None]
