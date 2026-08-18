from __future__ import annotations

"""Composition root for the module 4 API.

``create_app`` takes every collaborator as an optional argument so tests can inject a
temp-file database, a fixed-clock engine, and a fake AI provider without patching
globals. The module-level ``app`` is what uvicorn serves.

Run from the repository root — there is no ``pyproject.toml``, so ``shared`` and the
sibling modules only resolve when the repo root is on ``sys.path``:

    uvicorn module_4_api_ui.backend.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from module_4_api_ui.backend.audit_engine.stub_engine import StubAuditEngine
from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.errors import ApiError
from module_4_api_ui.backend.repositories import audit_run_repository
from module_4_api_ui.backend.routers import (
	audit_runs,
	batches,
	catalog,
	compliance,
	explanations,
	findings,
	health,
	resolution,
)
from module_4_api_ui.backend.services.job_registry import JobRegistry
from shared.database.session import (
	create_all_tables,
	create_engine_from_config,
	create_session_factory_for_engine,
)


logger = logging.getLogger("clinical_auditor.api")

API_PREFIX = "/api/v1"
API_TITLE = "Clinical Data Integrity Auditor API"
API_VERSION = "0.1.0"
API_DESCRIPTION = (
	"Audit-only service interface for the AI-Powered Clinical Data Integrity Auditor. "
	"Deterministic rules establish contradictions; AI supplies explanation and confidence "
	"context only and never changes a finding's status."
)


def _configure_logging() -> None:
	if logging.getLogger().handlers:
		return
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
	)
	# The HTTP client libraries log a line per request at INFO, which buries our own
	# output during test runs and adds nothing in production.
	for noisy in ("httpx", "httpx2", "httpcore", "httpcore2"):
		logging.getLogger(noisy).setLevel(logging.WARNING)


def resolve_audit_engine(config: ApiConfig) -> Any:
	"""Prefer module 2's real engine, fall back to the placeholder.

	``module_2_audit_engine.contradiction_detector`` is currently a valid but empty
	module, so importing it succeeds and only the attribute lookup fails. Both failures
	have to be caught for the fallback to work.
	"""
	if config.audit_engine in {"auto", "module_2"}:
		try:
			from module_2_audit_engine.contradiction_detector import (  # type: ignore[attr-defined]
				ContradictionDetector,
			)

			logger.info("Using module_2_audit_engine.ContradictionDetector")
			return ContradictionDetector()
		except (ImportError, AttributeError):
			if config.audit_engine == "module_2":
				raise
			logger.warning(
				"module_2_audit_engine is not implemented yet; using StubAuditEngine placeholder"
			)

	return StubAuditEngine()


def build_ai_orchestrator(config: ApiConfig) -> Any | None:
	"""Construct module 3's orchestrator once, at startup.

	Construction reads three prompt files from disk, so it must not happen per request.
	The Bedrock client itself is created lazily on first call, so no AWS credentials are
	needed to boot — a missing credential surfaces as a failed explanation job, not a
	dead server.
	"""
	if not config.ai_enabled:
		logger.info("AI explanation disabled (AI_ENABLED=false)")
		return None

	try:
		from module_3_ai_reasoning.llm.provider import BedrockLLMProvider
		from module_3_ai_reasoning.orchestrator import AIReasoningOrchestrator

		provider_kwargs: dict[str, Any] = {}
		if config.bedrock_model_id:
			provider_kwargs["model_id"] = config.bedrock_model_id
		if config.aws_region:
			provider_kwargs["region"] = config.aws_region

		return AIReasoningOrchestrator(provider=BedrockLLMProvider(**provider_kwargs))
	except Exception:
		logger.exception("Could not initialise AI reasoning; explanations will be unavailable")
		return None


def create_app(
	config: ApiConfig | None = None,
	session_factory: "sessionmaker[Session] | None" = None,
	audit_engine: Any | None = None,
	ai_orchestrator: Any | None = None,
) -> FastAPI:
	_configure_logging()
	resolved_config = config or ApiConfig.from_env()

	@asynccontextmanager
	async def lifespan(application: FastAPI) -> AsyncIterator[None]:
		engine = None
		if session_factory is None:
			engine = create_engine_from_config(resolved_config.database_config)
			if resolved_config.auto_create_tables:
				try:
					create_all_tables(engine)
				except Exception:
					# A missing database must not stop the app from booting; /health
					# reports database_reachable=false so the UI can explain it.
					logger.exception("Could not create tables at startup")
			application.state.session_factory = create_session_factory_for_engine(engine)
		else:
			application.state.session_factory = session_factory

		application.state.config = resolved_config
		application.state.audit_engine = audit_engine or resolve_audit_engine(resolved_config)
		application.state.ai_orchestrator = ai_orchestrator or build_ai_orchestrator(resolved_config)
		application.state.job_registry = JobRegistry()

		# Background execution is in-process, so a restart can leave runs stranded in
		# "queued"/"running" with nothing left to advance them.
		try:
			with application.state.session_factory() as session:
				stranded = audit_run_repository.fail_orphaned_runs(session)
				if stranded:
					session.commit()
					logger.warning("Marked %s stranded audit run(s) as failed", stranded)
		except Exception:
			logger.exception("Could not reconcile stranded audit runs at startup")

		try:
			yield
		finally:
			if engine is not None:
				engine.dispose()

	application = FastAPI(
		title=API_TITLE,
		version=API_VERSION,
		description=API_DESCRIPTION,
		lifespan=lifespan,
	)

	application.add_middleware(
		CORSMiddleware,
		allow_origins=list(resolved_config.cors_origins),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	@application.exception_handler(ApiError)
	async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
		return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

	@application.exception_handler(RequestValidationError)
	async def _handle_validation_error(
		request: Request, exc: RequestValidationError
	) -> JSONResponse:
		return JSONResponse(
			status_code=422,
			content={
				"error": "request_validation_error",
				"detail": "Request payload failed validation.",
				# pydantic v2 can put exception objects in a error's ``ctx``; encode
				# before handing it to JSONResponse or serialization blows up.
				"context": {"errors": jsonable_encoder(exc.errors())},
			},
		)

	application.include_router(health.router, prefix=API_PREFIX)
	application.include_router(batches.router, prefix=API_PREFIX)
	application.include_router(audit_runs.router, prefix=API_PREFIX)
	application.include_router(findings.router, prefix=API_PREFIX)
	application.include_router(explanations.router, prefix=API_PREFIX)
	application.include_router(resolution.router, prefix=API_PREFIX)
	application.include_router(catalog.router, prefix=API_PREFIX)
	application.include_router(compliance.router, prefix=API_PREFIX)
	return application


app = create_app()
