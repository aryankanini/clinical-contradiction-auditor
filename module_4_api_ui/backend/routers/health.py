from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.dependencies import get_config, get_session_factory
from module_4_api_ui.backend.schemas.common import HealthOut


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def read_health(
	request: Request,
	config: ApiConfig = Depends(get_config),
	session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> HealthOut:
	"""Liveness plus the two facts that most often explain a broken environment.

	Reports database reachability rather than refusing to boot without it, so the UI can
	render a useful error instead of failing to load.
	"""
	database_reachable = True
	try:
		with session_factory() as session:
			session.execute(text("SELECT 1"))
	except Exception:
		database_reachable = False

	engine = request.app.state.audit_engine
	return HealthOut(
		status="ok",
		database_reachable=database_reachable,
		audit_engine=type(engine).__name__,
		audit_engine_is_placeholder=bool(getattr(engine, "is_placeholder", False)),
		ai_enabled=config.ai_enabled,
	)
