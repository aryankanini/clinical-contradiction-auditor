from __future__ import annotations

"""Compliance sampling, reproducibility verification, and export (UC-005)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.dependencies import get_config, get_session, require_roles
from module_4_api_ui.backend.schemas.compliance import (
	EvidenceBundleOut,
	ExportRequest,
	SampleOut,
	SampleSelectRequest,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.compliance_service import ComplianceService


router = APIRouter(prefix="/compliance", tags=["compliance"])


def _service(config: ApiConfig = Depends(get_config)) -> ComplianceService:
	return ComplianceService(config)


@router.post("/samples", response_model=SampleOut)
def select_sample(
	payload: SampleSelectRequest,
	session: Session = Depends(get_session),
	service: ComplianceService = Depends(_service),
	principal: Principal = Depends(require_roles("compliance")),
) -> SampleOut:
	"""Draw a seeded, reproducible sample of findings for audit review."""
	return service.select_sample(session, payload)


@router.post("/exports", response_model=EvidenceBundleOut)
def export_evidence_bundle(
	payload: ExportRequest,
	session: Session = Depends(get_session),
	service: ComplianceService = Depends(_service),
	principal: Principal = Depends(require_roles("compliance")),
) -> EvidenceBundleOut:
	return service.export(
		session, payload.finding_ids, payload.include_replay_snapshots, principal
	)
