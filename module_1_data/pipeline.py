from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Mapping

from module_1_data.ingestion.fhir_loader import stage_fhir_records
from module_1_data.ingestion.parser import (
	assess_normalized_resources,
	emit_governed_missing_relationship_signals,
	normalize_staged_resources,
	validate_batch_contract,
)
from module_1_data.persistence.artifact_store import load_replay_artifact, persist_ingest_artifacts
from shared.models.ingest_provenance import IngestProvenance
from shared.models.replay_artifact import ReplayArtifact
from shared.models.staged_resource import IngestRunResult


DEFAULT_ARTIFACT_DIR = Path("data") / "processed" / "ingest-artifacts"


def _build_provenance(
	result_status: str,
	metadata: Mapping[str, Any],
	normalized_resources: list[Any],
	validation_states: list[Any],
	replay_artifact_id: str,
) -> IngestProvenance:
	normalization_summary = {
		"normalized_resource_count": len(normalized_resources),
		"derived_status_count": sum(1 for item in normalized_resources if item.status.state == "derived"),
	}
	validation_summary = {
		"rule_ready_count": sum(1 for state in validation_states if state.rule_ready),
		"generic_incomplete_count": sum(1 for state in validation_states if state.generic_incompleteness),
		"governed_signal_count": sum(len(state.governed_signals) for state in validation_states),
	}
	return IngestProvenance(
		provenance_id=f"prov-{metadata.get('batch_id', 'unknown')}",
		batch_id=str(metadata.get("batch_id", "unknown")),
		source=str(metadata.get("source", "unknown")),
		ingest_status=result_status,
		counts={
			"accepted_count": int(metadata.get("accepted_count", 0)),
			"quarantined_count": int(metadata.get("quarantined_count", 0)),
			"loader_success_count": int(metadata.get("loader_success_count", 0)),
			"loader_failure_count": int(metadata.get("loader_failure_count", 0)),
		},
		normalization_summary=normalization_summary,
		validation_summary=validation_summary,
		replay_artifact_id=replay_artifact_id,
	)


def _build_replay_artifact(
	metadata: Mapping[str, Any],
	normalized_resources: list[Any],
	validation_states: list[Any],
	quarantined_records: list[Mapping[str, Any]],
	loader_failures: list[Dict[str, Any]],
) -> ReplayArtifact:
	artifact_id = f"replay-{metadata.get('batch_id', 'unknown')}"
	state_by_id = {state.record_id: state for state in validation_states}
	snapshots = []
	for resource in normalized_resources:
		state = state_by_id[resource.record_id]
		snapshots.append(
			{
				"record_id": resource.record_id,
				"resource_type": resource.resource_type,
				"family": resource.family,
				"status": resource.status.value,
				"status_state": resource.status.state.value,
				"timestamps": {name: field.value for name, field in resource.timestamps.items()},
				"references": {name: ref.reference for name, ref in resource.references.items()},
				"incomplete_fields": list(state.incomplete_fields),
				"unresolved_links": list(state.unresolved_links),
				"governed_signals": [signal.rule_id for signal in state.governed_signals],
			}
		)
	return ReplayArtifact(
		artifact_id=artifact_id,
		provenance_id=f"prov-{metadata.get('batch_id', 'unknown')}",
		snapshots=snapshots,
		quarantined_records=quarantined_records,
		loader_failures=loader_failures,
	)


def reconstruct_ingest_output(replay_artifact: ReplayArtifact) -> list[Dict[str, Any]]:
	return replay_artifact.reconstruct()


def reconstruct_ingest_output_from_path(replay_artifact_path: str | Path) -> list[Dict[str, Any]]:
	return load_replay_artifact(replay_artifact_path).reconstruct()


def ingest_batch(payload: Mapping[str, Any], artifact_dir: str | Path | None = None) -> IngestRunResult:
	validation_result = validate_batch_contract(payload)
	metadata: Dict[str, Any] = dict(validation_result.metadata)

	staged_resources = []
	loader_failures = []
	normalized_resources = []
	validation_states = []
	governed_signals = []
	provenance = None
	replay_artifact = None
	if validation_result.is_accepted:
		batch_id = str(metadata["batch_id"])
		source = str(metadata["source"])
		loader_result = stage_fhir_records(batch_id, source, validation_result.accepted_records)
		staged_resources = loader_result.staged_resources
		loader_failures = [failure.__dict__ for failure in loader_result.failures]
		normalized_resources = normalize_staged_resources(staged_resources)
		validation_states = assess_normalized_resources(normalized_resources)
		governed_signal_objects = emit_governed_missing_relationship_signals(normalized_resources, validation_states)
		governed_signals = [signal.__dict__ for signal in governed_signal_objects]
		metadata.update(
			{
				"loader_success_count": loader_result.success_count,
				"loader_failure_count": loader_result.failure_count,
			}
		)
		replay_artifact = _build_replay_artifact(
			metadata,
			normalized_resources,
			validation_states,
			validation_result.quarantined_records,
			loader_failures,
		)
		provenance = _build_provenance(
			validation_result.status,
			metadata,
			normalized_resources,
			validation_states,
			replay_artifact.artifact_id,
		)
		artifact_paths = persist_ingest_artifacts(
			Path(artifact_dir) if artifact_dir is not None else DEFAULT_ARTIFACT_DIR,
			provenance,
			replay_artifact,
		)
		provenance = replace(provenance, storage_path=artifact_paths["provenance_path"])
		replay_artifact = replace(replay_artifact, storage_path=artifact_paths["replay_artifact_path"])
		metadata.update(artifact_paths)
	else:
		metadata.update({"loader_success_count": 0, "loader_failure_count": 0})

	return IngestRunResult(
		status=validation_result.status,
		metadata=metadata,
		staged_resources=staged_resources,
		quarantined_records=validation_result.quarantined_records,
		validation_errors=[error.__dict__ for error in validation_result.errors],
		loader_failures=loader_failures,
		normalized_resources=normalized_resources,
		validation_states=validation_states,
		governed_signals=governed_signals,
		provenance=provenance,
		replay_artifact=replay_artifact,
	)


