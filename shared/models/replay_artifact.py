from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class ReplayArtifact:
	artifact_id: str
	provenance_id: str
	snapshots: List[Dict[str, Any]] = field(default_factory=list)
	quarantined_records: List[Mapping[str, Any]] = field(default_factory=list)
	loader_failures: List[Dict[str, Any]] = field(default_factory=list)
	storage_path: str | None = None

	def reconstruct(self) -> List[Dict[str, Any]]:
		return list(self.snapshots)
