from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

from shared.models.staged_resource import (
	LoaderFailure,
	LoaderResult,
	RESOURCE_FAMILY_BY_TYPE,
	StagedResource,
)

Loader = Callable[[str, str, Mapping[str, Any]], StagedResource]


def _stage_resource(batch_id: str, source: str, record: Mapping[str, Any]) -> StagedResource:
	resource_type = str(record["resourceType"])
	record_id = str(record["id"])
	family = RESOURCE_FAMILY_BY_TYPE[resource_type]
	return StagedResource(
		batch_id=batch_id,
		source=source,
		family=family,
		resource_type=resource_type,
		record_id=record_id,
		payload=record,
	)


LOADERS: Dict[str, Loader] = {
	resource_type: _stage_resource for resource_type in RESOURCE_FAMILY_BY_TYPE
}


def stage_fhir_records(batch_id: str, source: str, records: list[Mapping[str, Any]]) -> LoaderResult:
	staged_resources: list[StagedResource] = []
	failures: list[LoaderFailure] = []

	for record in records:
		resource_type = record.get("resourceType") if isinstance(record, Mapping) else None
		record_id = record.get("id") if isinstance(record, Mapping) else None

		if resource_type not in LOADERS:
			failures.append(
				LoaderFailure(
					record_id=str(record_id) if record_id else None,
					resource_type=str(resource_type) if resource_type else None,
					reason="no loader registered for resourceType",
				)
			)
			continue

		try:
			staged_resources.append(LOADERS[str(resource_type)](batch_id, source, record))
		except Exception as exc:  # pragma: no cover - defensive catch for partial-ingest behavior
			failures.append(
				LoaderFailure(
					record_id=str(record_id) if record_id else None,
					resource_type=str(resource_type),
					reason=str(exc),
				)
			)

	return LoaderResult(staged_resources=staged_resources, failures=failures)

