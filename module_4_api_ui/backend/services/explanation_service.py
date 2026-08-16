from __future__ import annotations

"""AI explanation generation (FR-007, FR-011).

Module 3 establishes nothing: it explains findings the deterministic engine already
made. Two invariants are enforced here and asserted in tests:

* generating or refreshing an explanation never touches ``FindingRow.status``;
* every persisted explanation carries the audit-only disclaimer.
"""

import asyncio
import logging
from dataclasses import asdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.disclaimers import AI_AUDIT_ONLY_DISCLAIMER
from module_4_api_ui.backend.errors import NotFoundError, UpstreamUnavailableError
from module_4_api_ui.backend.repositories import finding_repository
from module_4_api_ui.backend.services.job_registry import JobRegistry
from shared.database.models import AIExplanationRow, FindingRow


logger = logging.getLogger("clinical_auditor.api.explanation")

JOB_KIND = "explanation"


def _evidence_records(finding: FindingRow) -> List[Dict[str, Any]]:
	"""Shape a finding's evidence the way module 3's agents expect.

	The agents read ``resource_type``, ``record_id``, ``status``, ``status_state``,
	``timestamps``, ``incomplete_fields``, and ``unresolved_links`` — the same replay
	snapshot shape the engine consumes, so nothing needs reshaping here.
	"""
	records: List[Dict[str, Any]] = []
	for item in finding_repository.engine_evidence(finding):
		payload = dict(item.evidence_payload or {})
		resource = item.normalized_resource
		records.append(
			{
				"record_id": resource.record_external_id if resource else payload.get("record_id"),
				"resource_type": resource.resource_type if resource else payload.get("resource_type"),
				"status": resource.status_value if resource else payload.get("status"),
				"status_state": resource.status_state if resource else payload.get("status_state"),
				"timestamps": payload.get("timestamps") or {},
				"incomplete_fields": payload.get("incomplete_fields") or [],
				"unresolved_links": payload.get("unresolved_links") or [],
			}
		)
	return records


class ExplanationService:
	def __init__(
		self,
		session_factory: "sessionmaker[Session]",
		config: ApiConfig,
		orchestrator: Any | None = None,
		job_registry: JobRegistry | None = None,
	) -> None:
		self._session_factory = session_factory
		self._config = config
		self._orchestrator = orchestrator
		self._jobs = job_registry

	def _require_orchestrator(self) -> Any:
		if not self._config.ai_enabled:
			raise UpstreamUnavailableError(
				"AI explanation is disabled (AI_ENABLED=false). Deterministic findings and "
				"evidence remain fully available.",
				code="ai_disabled",
			)
		if self._orchestrator is None:
			raise UpstreamUnavailableError(
				"AI reasoning is not configured on this server.",
				code="ai_unavailable",
			)
		return self._orchestrator

	async def generate(self, finding_id: int, requested_by: str) -> None:
		"""Produce and persist an explanation. Never alters the finding itself."""
		key = (JOB_KIND, finding_id)
		if self._jobs is not None:
			await self._jobs.start(key)

		try:
			orchestrator = self._require_orchestrator()
			context = await run_in_threadpool(self._load_context, finding_id)

			result = await asyncio.wait_for(
				orchestrator.reason(
					finding_id=str(finding_id),
					rule_id=context["rule_id"],
					finding_type=context["finding_type"],
					summary=context["summary"],
					severity=context["severity"],
					evidence_records=context["evidence_records"],
				),
				timeout=self._config.ai_timeout_seconds,
			)

			await run_in_threadpool(self._persist, finding_id, result)
			if self._jobs is not None:
				await self._jobs.succeed(key)
			logger.info("Generated AI explanation for finding %s", finding_id)

		except asyncio.TimeoutError:
			message = f"AI provider timed out after {self._config.ai_timeout_seconds:.0f}s."
			logger.warning("AI explanation timed out for finding %s", finding_id)
			if self._jobs is not None:
				await self._jobs.fail(key, message)
		except Exception as exc:  # noqa: BLE001 - a background job must record its failure
			# Module 3 wraps no botocore errors and its prompt templates use str.format,
			# so a throttle, a missing credential, or a stray brace all surface here.
			# The finding stays fully usable without AI; only the job is marked failed.
			logger.exception("AI explanation failed for finding %s", finding_id)
			if self._jobs is not None:
				await self._jobs.fail(key, f"{type(exc).__name__}: {exc}")

	def _load_context(self, finding_id: int) -> Dict[str, Any]:
		with self._session_factory() as session:
			finding = finding_repository.get_finding_with_relations(session, finding_id)
			if finding is None:
				raise NotFoundError(f"Finding {finding_id} was not found.")
			return {
				"rule_id": finding.rule_id,
				"finding_type": finding.finding_type,
				"summary": finding.summary,
				"severity": finding.severity,
				"evidence_records": _evidence_records(finding),
			}

	def _persist(self, finding_id: int, result: Any) -> int:
		"""Write the explanation only. ``FindingRow`` is deliberately untouched (FR-007)."""
		evidence = asdict(result.evidence) if result.evidence else None
		draft = asdict(result.resolution_draft) if result.resolution_draft else None
		confidence_context = (result.confidence_context or "").strip()

		if draft is not None:
			# Module 3 splits the model's reply on a literal sentence; when that split
			# degrades, rationale echoes the action. Either way the draft is unreliable,
			# and UC-003 ext 2a requires manual entry rather than a silent bad default.
			draft["low_confidence"] = (
				not confidence_context or draft.get("rationale") == draft.get("suggested_action")
			)

		with self._session_factory() as session:
			row = AIExplanationRow(
				finding_id=finding_id,
				model_name=result.model_name,
				prompt_version=result.prompt_version,
				rationale_text=result.contradiction_explanation,
				confidence_json={
					"confidence_context": confidence_context,
					"evidence": evidence,
					"resolution_draft": draft,
					"disclaimer": AI_AUDIT_ONLY_DISCLAIMER,
				},
			)
			session.add(row)
			session.commit()
			return row.id
