from __future__ import annotations

"""Batch intake and inspection (UC-001, FR-001/FR-002).

Handlers are ``def`` rather than ``async def`` on purpose: ``ingest_batch`` and every
SQLAlchemy call here is blocking, so FastAPI runs them in its worker threadpool. Marking
them ``async`` would stall the event loop instead.
"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.dependencies import (
	get_config,
	get_principal,
	get_session,
	require_roles,
)
from module_4_api_ui.backend.errors import ValidationError
from module_4_api_ui.backend.schemas.batches import (
	BatchDetailOut,
	BatchIngestRequest,
	BatchIngestResponse,
	BatchSummaryOut,
	NormalizedResourceOut,
)
from module_4_api_ui.backend.schemas.common import Page
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.batch_service import BatchService


router = APIRouter(prefix="/batches", tags=["batches"])


def _service(config: ApiConfig = Depends(get_config)) -> BatchService:
	return BatchService(config)


@router.post("", response_model=BatchIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_batch_payload(
	payload: BatchIngestRequest,
	response: Response,
	session: Session = Depends(get_session),
	service: BatchService = Depends(_service),
	principal: Principal = Depends(require_roles("steward", "analyst")),
) -> BatchIngestResponse:
	result = service.ingest(session, payload.model_dump())
	if result.ingest_status == "partial-ingest":
		# Some records were quarantined; the caller needs to see what did not land.
		response.status_code = status.HTTP_207_MULTI_STATUS
	return result


@router.post("/upload", response_model=BatchIngestResponse, status_code=status.HTTP_201_CREATED)
def upload_batch_file(
	response: Response,
	file: UploadFile = File(...),
	session: Session = Depends(get_session),
	service: BatchService = Depends(_service),
	principal: Principal = Depends(require_roles("steward", "analyst")),
) -> BatchIngestResponse:
	raw = file.file.read()
	try:
		payload: Dict[str, Any] = json.loads(raw)
	except ValueError as exc:
		raise ValidationError(
			"Uploaded file is not valid JSON.",
			context={"filename": file.filename, "reason": str(exc)},
		) from exc

	if not isinstance(payload, dict):
		raise ValidationError(
			"Uploaded JSON must be a batch object.",
			context={"filename": file.filename},
		)

	result = service.ingest(session, payload)
	if result.ingest_status == "partial-ingest":
		response.status_code = status.HTTP_207_MULTI_STATUS
	return result


@router.get("", response_model=Page[BatchSummaryOut])
def list_batches(
	batch_status: str | None = Query(default=None, alias="status"),
	source: str | None = Query(default=None),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=25, ge=1, le=200),
	session: Session = Depends(get_session),
	service: BatchService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> Page[BatchSummaryOut]:
	items, total = service.list_batches(
		session, status=batch_status, source=source, page=page, page_size=page_size
	)
	return Page.build(items, total, page, page_size)


@router.get("/{batch_id}", response_model=BatchDetailOut)
def read_batch(
	batch_id: int,
	session: Session = Depends(get_session),
	service: BatchService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> BatchDetailOut:
	return service.detail(session, batch_id)


@router.get("/{batch_id}/resources", response_model=Page[NormalizedResourceOut])
def list_batch_resources(
	batch_id: int,
	resource_type: str | None = Query(default=None),
	rule_ready: bool | None = Query(default=None),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=50, ge=1, le=200),
	session: Session = Depends(get_session),
	service: BatchService = Depends(_service),
	principal: Principal = Depends(get_principal),
) -> Page[NormalizedResourceOut]:
	items, total = service.list_resources(
		session,
		batch_id,
		resource_type=resource_type,
		rule_ready=rule_ready,
		page=page,
		page_size=page_size,
	)
	return Page.build(items, total, page, page_size)
