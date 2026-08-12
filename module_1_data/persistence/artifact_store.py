from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from shared.models.ingest_provenance import IngestProvenance
from shared.models.replay_artifact import ReplayArtifact


def _ensure_dir(artifact_dir: Path) -> Path:
	artifact_dir.mkdir(parents=True, exist_ok=True)
	return artifact_dir


def persist_ingest_artifacts(
	artifact_dir: Path,
	provenance: IngestProvenance,
	replay_artifact: ReplayArtifact,
) -> dict[str, str]:
	directory = _ensure_dir(artifact_dir)
	provenance_path = directory / f"{provenance.provenance_id}.json"
	replay_path = directory / f"{replay_artifact.artifact_id}.json"

	provenance_path.write_text(json.dumps(asdict(provenance), indent=2), encoding="utf-8")
	replay_path.write_text(json.dumps(asdict(replay_artifact), indent=2), encoding="utf-8")

	return {
		"provenance_path": str(provenance_path),
		"replay_artifact_path": str(replay_path),
	}


def load_replay_artifact(replay_artifact_path: str | Path) -> ReplayArtifact:
	payload: dict[str, Any] = json.loads(Path(replay_artifact_path).read_text(encoding="utf-8"))
	return ReplayArtifact(**payload)
