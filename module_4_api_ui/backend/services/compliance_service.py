from __future__ import annotations

"""Compliance sampling, reproducibility, and export (UC-005, FR-006, FR-012)."""

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from module_1_data.pipeline import reconstruct_ingest_output_from_path
from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.errors import NotFoundError
from module_4_api_ui.backend.repositories import batch_repository, finding_repository
from module_4_api_ui.backend.schemas.compliance import (
	EvidenceBundleItemOut,
	EvidenceBundleOut,
	ReproducibilityCheckOut,
	ReproducibilityOut,
	SampleOut,
	SampleSelectRequest,
)
from module_4_api_ui.backend.security import Principal
from module_4_api_ui.backend.services.finding_service import FindingService
from shared.database.models import AuditRunRow, FindingRow


logger = logging.getLogger("clinical_auditor.api.compliance")


class ComplianceService:
	def __init__(self, config: ApiConfig, finding_service: FindingService | None = None) -> None:
		self._config = config
		self._findings = finding_service or FindingService()

	def select_sample(self, session: Session, request: SampleSelectRequest) -> SampleOut:
		"""Pick a reproducible sample.

		Selection is seeded and drawn from a sorted candidate list, so re-running the
		same criteria returns the same findings. That is what lets a reviewer reproduce a
		colleague's sample without storing it.
		"""
		statement = select(FindingRow.id)
		if request.audit_run_id is not None:
			statement = statement.where(FindingRow.audit_run_id == request.audit_run_id)
		if request.batch_id is not None:
			statement = statement.join(
				AuditRunRow, FindingRow.audit_run_id == AuditRunRow.id
			).where(AuditRunRow.batch_id == request.batch_id)
		if request.severity:
			statement = statement.where(FindingRow.severity.in_(request.severity))
		if request.status:
			statement = statement.where(FindingRow.status.in_(request.status))

		candidates = sorted(int(row) for row in session.execute(statement).scalars().all())
		size = min(request.sample_size, len(candidates))
		selected = sorted(random.Random(request.seed).sample(candidates, size)) if size else []

		criteria = request.model_dump()
		return SampleOut(
			sample_id=f"sample-{request.seed}-{size}",
			criteria=criteria,
			finding_ids=selected,
			candidate_count=len(candidates),
			selected_at=datetime.now(timezone.utc),
		)

	def reproducibility(self, session: Session, finding_id: int) -> ReproducibilityOut:
		"""Verify a finding can be rebuilt from stored artifacts (FR-012).

		Deliberately reads the replay artifact rather than re-running ingestion — the
		BRD requires reproducing findings "without re-running the full pipeline".
		"""
		finding = finding_repository.get_finding_with_relations(session, finding_id)
		if finding is None:
			raise NotFoundError(f"Finding {finding_id} was not found.")

		checks: List[ReproducibilityCheckOut] = []
		missing: List[str] = []

		run = finding.audit_run
		rule_pack_version = run.rule_pack.version if run and run.rule_pack else None
		checks.append(
			ReproducibilityCheckOut(
				name="rule_pack_resolvable",
				passed=rule_pack_version is not None,
				detail=f"Rule pack: {rule_pack_version or 'missing'}",
			)
		)
		if rule_pack_version is None:
			missing.append("rule_pack")

		evidence = finding_repository.engine_evidence(finding)
		expected_ids = sorted(
			{
				item.normalized_resource.record_external_id
				if item.normalized_resource
				else str(item.evidence_payload.get("record_id") or "")
				for item in evidence
			}
			- {""}
		)
		checks.append(
			ReproducibilityCheckOut(
				name="evidence_present",
				passed=bool(expected_ids),
				detail=f"{len(expected_ids)} evaluated record(s) referenced",
			)
		)
		if not expected_ids:
			missing.append("evidence")

		batch = batch_repository.get_batch(session, run.batch_id) if run else None
		artifact_path = batch.replay_artifact_path if batch else None

		snapshots = self._load_snapshots(artifact_path)
		if snapshots is None:
			# UC-005 ext 2a: a missing artifact is a failed reproducibility result, not
			# a server error.
			checks.append(
				ReproducibilityCheckOut(
					name="replay_artifact_readable",
					passed=False,
					detail=f"Replay artifact unavailable: {artifact_path or 'not recorded'}",
				)
			)
			missing.append("replay_artifact")
		else:
			checks.append(
				ReproducibilityCheckOut(
					name="replay_artifact_readable",
					passed=True,
					detail=f"{len(snapshots)} snapshot(s) reconstructed from {artifact_path}",
				)
			)
			snapshot_ids = {str(item.get("record_id")) for item in snapshots}
			unmatched = [rid for rid in expected_ids if rid not in snapshot_ids]
			checks.append(
				ReproducibilityCheckOut(
					name="evidence_reconstructable",
					passed=not unmatched,
					detail=(
						"All evaluated records present in the replay artifact"
						if not unmatched
						else f"Missing from replay artifact: {', '.join(unmatched)}"
					),
				)
			)
			if unmatched:
				missing.append("evidence_records")

		return ReproducibilityOut(
			finding_id=finding_id,
			reproducible=all(check.passed for check in checks),
			checks=checks,
			missing_artifacts=missing,
			verified_at=datetime.now(timezone.utc),
		)

	def export(
		self,
		session: Session,
		finding_ids: List[int],
		include_snapshots: bool,
		principal: Principal,
	) -> EvidenceBundleOut:
		generated_at = datetime.now(timezone.utc)
		sample_id = f"export-{generated_at.strftime('%Y%m%dT%H%M%S')}"
		items: List[EvidenceBundleItemOut] = []

		for finding_id in finding_ids:
			detail = self._findings.detail(session, finding_id, principal)
			finding = finding_repository.get_finding_with_relations(session, finding_id)
			run = finding.audit_run if finding else None
			batch = batch_repository.get_batch(session, run.batch_id) if run else None

			snapshots: List[Dict[str, Any]] = []
			if include_snapshots and batch is not None:
				loaded = self._load_snapshots(batch.replay_artifact_path)
				if loaded is not None:
					evaluated = set(detail.transparency.records_evaluated)
					snapshots = [
						item for item in loaded if str(item.get("record_id")) in evaluated
					]

			items.append(
				EvidenceBundleItemOut(
					finding=detail,
					batch_external_id=batch.batch_external_id if batch else None,
					rule_pack_version=detail.transparency.rule_pack_version,
					replay_snapshots=snapshots,
					reproducibility=self.reproducibility(session, finding_id),
				)
			)

		bundle = EvidenceBundleOut(
			sample_id=sample_id,
			generated_at=generated_at,
			generated_by=principal.user_id,
			items=items,
		)

		export_path = self._write_bundle(sample_id, bundle)
		return bundle.model_copy(update={"export_path": export_path})

	# --- helpers --------------------------------------------------------

	@staticmethod
	def _load_snapshots(artifact_path: str | None) -> List[Dict[str, Any]] | None:
		if not artifact_path:
			return None
		try:
			return reconstruct_ingest_output_from_path(artifact_path)
		except (OSError, ValueError, KeyError):
			logger.warning("Replay artifact could not be read: %s", artifact_path)
			return None

	def _write_bundle(self, sample_id: str, bundle: EvidenceBundleOut) -> str | None:
		try:
			directory = Path(self._config.export_dir)
			directory.mkdir(parents=True, exist_ok=True)
			path = directory / f"{sample_id}.json"
			path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
			return str(path)
		except OSError:
			# UC-005 ext 3a: a failed write is logged, but the caller still receives the
			# bundle in the response body.
			logger.exception("Could not write compliance export bundle %s", sample_id)
			return None
