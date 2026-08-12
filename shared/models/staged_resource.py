from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Mapping

ResourceFamily = Literal["Condition", "Medication", "Procedure", "Encounter", "Observation", "CarePlan"]

RESOURCE_FAMILY_BY_TYPE: Dict[str, ResourceFamily] = {
    "Condition": "Condition",
    "MedicationRequest": "Medication",
    "Procedure": "Procedure",
    "Encounter": "Encounter",
    "Observation": "Observation",
    "CarePlan": "CarePlan",
}


@dataclass(frozen=True)
class StagedResource:
    batch_id: str
    source: str
    family: ResourceFamily
    resource_type: str
    record_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class LoaderFailure:
    record_id: str | None
    resource_type: str | None
    reason: str


@dataclass(frozen=True)
class LoaderResult:
    staged_resources: List[StagedResource] = field(default_factory=list)
    failures: List[LoaderFailure] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.staged_resources)

    @property
    def failure_count(self) -> int:
        return len(self.failures)


@dataclass(frozen=True)
class IngestRunResult:
    status: str
    metadata: Dict[str, Any]
    staged_resources: List[StagedResource] = field(default_factory=list)
    quarantined_records: List[Mapping[str, Any]] = field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    loader_failures: List[Dict[str, Any]] = field(default_factory=list)
    normalized_resources: List[Any] = field(default_factory=list)
    validation_states: List[Any] = field(default_factory=list)
    governed_signals: List[Dict[str, Any]] = field(default_factory=list)
    provenance: Any | None = None
    replay_artifact: Any | None = None
