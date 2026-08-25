from __future__ import annotations

from typing import Any, Iterable, Mapping

from module_2_audit_engine.rules.timeline_rules import expected_relationships_for
from shared.enums.normalization_state import NormalizationState
from shared.models.batch_contract import BatchValidationResult, validate_batch_payload
from shared.models.normalized_resource import NormalizedField, NormalizedReference, NormalizedResource
from shared.models.staged_resource import StagedResource
from shared.models.validation_state import MissingRelationshipSignal, ResourceValidationState


STATUS_PATHS = {
	"Condition": ("clinicalStatus", "status"),
	"MedicationRequest": ("status",),
	"Procedure": ("status",),
	"Encounter": ("status",),
	"Observation": ("status",),
	"CarePlan": ("status",),
}

TIMESTAMP_PATHS = {
	"Condition": ("recordedDate", "onsetDateTime"),
	"MedicationRequest": ("authoredOn",),
	"Procedure": ("performedDateTime", "occurrenceDateTime"),
	"Encounter": ("period.start",),
	"Observation": ("effectiveDateTime", "issued"),
	"CarePlan": ("period.start", "created"),
}

REFERENCE_FIELDS = {
	"Condition": ("subject", "encounter"),
	"MedicationRequest": ("subject", "encounter", "basedOn"),
	"Procedure": ("subject", "encounter", "basedOn"),
	"Encounter": ("subject", "basedOn"),
	"Observation": ("subject", "encounter", "basedOn"),
	"CarePlan": ("subject", "encounter", "basedOn"),
}


def _read_path(payload: Mapping[str, Any], path: str) -> Any:
	current: Any = payload
	for segment in path.split("."):
		if not isinstance(current, Mapping) or segment not in current:
			return None
		current = current[segment]
	return current


def _extract_status(resource: StagedResource) -> NormalizedField:
	for path in STATUS_PATHS.get(resource.resource_type, ("status",)):
		value = _read_path(resource.payload, path)
		if isinstance(value, str) and value:
			return NormalizedField(name="status", value=value, state=NormalizationState.VALID, source_path=path)
		if isinstance(value, Mapping):
			text = value.get("text")
			if isinstance(text, str) and text:
				return NormalizedField(name="status", value=text, state=NormalizationState.DERIVED, source_path=path + ".text")
			coding = value.get("coding")
			if isinstance(coding, list) and coding and isinstance(coding[0], Mapping):
				code = coding[0].get("code")
				if isinstance(code, str) and code:
					return NormalizedField(name="status", value=code, state=NormalizationState.DERIVED, source_path=path + ".coding[0].code")
	return NormalizedField(name="status", value=None, state=NormalizationState.MISSING, source_path="")


def _extract_timestamps(resource: StagedResource) -> dict[str, NormalizedField]:
	fields: dict[str, NormalizedField] = {}
	seen_values: dict[str, str] = {}
	for path in TIMESTAMP_PATHS.get(resource.resource_type, ()): 
		value = _read_path(resource.payload, path)
		name = path
		if isinstance(value, str) and value:
			state = NormalizationState.VALID
			if seen_values and value not in seen_values.values():
				state = NormalizationState.AMBIGUOUS
			fields[name] = NormalizedField(name=name, value=value, state=state, source_path=path)
			seen_values[name] = value
		else:
			fields[name] = NormalizedField(name=name, value=None, state=NormalizationState.MISSING, source_path=path)
	return fields


def _extract_references(resource: StagedResource, known_ids: Iterable[str]) -> dict[str, NormalizedReference]:
	known = set(known_ids)
	refs: dict[str, NormalizedReference] = {}
	for field_name in REFERENCE_FIELDS.get(resource.resource_type, ()): 
		value = _read_path(resource.payload, field_name)
		if isinstance(value, list):
			value = value[0] if value else None
		if not isinstance(value, Mapping):
			refs[field_name] = NormalizedReference(
				name=field_name,
				reference=None,
				target_id=None,
				state=NormalizationState.MISSING,
				source_path=field_name,
			)
			continue
		reference = value.get("reference")
		if not isinstance(reference, str) or not reference:
			refs[field_name] = NormalizedReference(field_name, None, None, NormalizationState.INVALID, field_name + ".reference")
			continue
		target_id = reference.split("/")[-1]
		state = NormalizationState.VALID if target_id in known else NormalizationState.UNRESOLVED
		refs[field_name] = NormalizedReference(field_name, reference, target_id, state, field_name + ".reference")
	return refs


def normalize_staged_resources(staged_resources: list[StagedResource]) -> list[NormalizedResource]:
	known_ids = [resource.record_id for resource in staged_resources]
	normalized: list[NormalizedResource] = []
	for resource in staged_resources:
		normalized.append(
			NormalizedResource(
				batch_id=resource.batch_id,
				source=resource.source,
				family=resource.family,
				resource_type=resource.resource_type,
				record_id=resource.record_id,
				status=_extract_status(resource),
				timestamps=_extract_timestamps(resource),
				references=_extract_references(resource, known_ids),
				provenance={
					"source_record_id": resource.record_id,
					"resource_type": resource.resource_type,
				},
				raw_payload=resource.payload,
			)
		)
	return normalized


def assess_normalized_resources(resources: list[NormalizedResource]) -> list[ResourceValidationState]:
	results: list[ResourceValidationState] = []
	for resource in resources:
		incomplete_fields: list[str] = []
		unresolved_links: list[str] = []

		if resource.status.state != NormalizationState.VALID and resource.status.state != NormalizationState.DERIVED:
			incomplete_fields.append("status")

		if resource.primary_timestamp.state in {NormalizationState.MISSING, NormalizationState.INVALID, NormalizationState.AMBIGUOUS}:
			incomplete_fields.append("timestamp")

		for field_name, reference in resource.references.items():
			if reference.state == NormalizationState.UNRESOLVED:
				unresolved_links.append(field_name)
			elif reference.state == NormalizationState.INVALID:
				incomplete_fields.append(field_name)

		results.append(
			ResourceValidationState(
				record_id=resource.record_id,
				resource_type=resource.resource_type,
				incomplete_fields=incomplete_fields,
				unresolved_links=unresolved_links,
				rule_ready=not incomplete_fields and not unresolved_links,
			)
		)
	return results


def emit_governed_missing_relationship_signals(
	resources: list[NormalizedResource],
	validation_states: list[ResourceValidationState],
) -> list[MissingRelationshipSignal]:
	signals: list[MissingRelationshipSignal] = []
	states_by_id = {state.record_id: state for state in validation_states}
	for resource in resources:
		state = states_by_id[resource.record_id]
		for relationship in expected_relationships_for(resource.resource_type):
			reference = resource.references.get(relationship)
			if reference is None or reference.state in {NormalizationState.MISSING, NormalizationState.UNRESOLVED, NormalizationState.INVALID}:
				signal = MissingRelationshipSignal(
					rule_id=f"REL-{resource.resource_type.upper()}-{relationship.upper()}",
					record_id=resource.record_id,
					resource_type=resource.resource_type,
					relationship_field=relationship,
					reason="expected relationship missing or unresolved",
				)
				signals.append(signal)
				state.governed_signals.append(signal)  # type: ignore[misc]
	return signals


def validate_batch_contract(payload: Mapping[str, Any]) -> BatchValidationResult:
	return validate_batch_payload(payload)

