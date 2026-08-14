from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from shared.enums.normalization_state import NormalizationState
from shared.models.staged_resource import ResourceFamily


@dataclass(frozen=True)
class NormalizedField:
	name: str
	value: Any
	state: NormalizationState
	source_path: str


@dataclass(frozen=True)
class NormalizedReference:
	name: str
	reference: str | None
	target_id: str | None
	state: NormalizationState
	source_path: str


@dataclass(frozen=True)
class NormalizedResource:
	batch_id: str
	source: str
	family: ResourceFamily
	resource_type: str
	record_id: str
	status: NormalizedField
	timestamps: Dict[str, NormalizedField] = field(default_factory=dict)
	references: Dict[str, NormalizedReference] = field(default_factory=dict)
	provenance: Dict[str, str] = field(default_factory=dict)
	raw_payload: Mapping[str, Any] = field(default_factory=dict)

	@property
	def primary_timestamp(self) -> NormalizedField:
		if self.timestamps:
			first_key = next(iter(self.timestamps))
			return self.timestamps[first_key]
		return NormalizedField(
			name="timestamp",
			value=None,
			state=NormalizationState.MISSING,
			source_path="",
		)
