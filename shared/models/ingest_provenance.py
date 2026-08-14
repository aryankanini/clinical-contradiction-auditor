from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class IngestProvenance:
	provenance_id: str
	batch_id: str
	source: str
	ingest_status: str
	counts: Dict[str, int] = field(default_factory=dict)
	normalization_summary: Dict[str, int] = field(default_factory=dict)
	validation_summary: Dict[str, int] = field(default_factory=dict)
	replay_artifact_id: str | None = None
	storage_path: str | None = None
