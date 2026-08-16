from __future__ import annotations

"""PLACEHOLDER deterministic engine for module 4 development.

    ============================================================
    THIS IS NOT THE PRODUCT'S AUDIT ENGINE.
    Owner of the real engine: module_2_audit_engine (Bharath).
    Replace this class by making module_2 satisfy AuditEnginePort;
    no API, schema, or UI change is required to swap it in.
    ============================================================

None of the rules below are authoritative clinical policy. They exist so the API and UI
are demoable before the deterministic engine lands, and so the seam is proven by real
data flowing through it rather than by fixtures.

Every rule reads only fields module 1 actually produces, and the pass is deterministic:
resources are sorted by record id, rules run in a fixed order, and the clock is
injected. The same batch therefore yields byte-identical findings, which is what makes
FR-012 reproducibility checkable.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from module_2_audit_engine.rules.timeline_rules import expected_relationships_for
from module_4_api_ui.backend.constants import (
	EVIDENCE_CONFLICTING_RECORD,
	EVIDENCE_GOVERNED_SIGNAL,
	FINDING_TYPE_CONTRADICTION,
	FINDING_TYPE_MISSING_RELATIONSHIP,
	FINDING_TYPE_STALE_STATE,
	FINDING_TYPE_TIMELINE_VIOLATION,
	OUTCOME_CONTRADICTION_CONFIRMED,
	OUTCOME_GAP_CONFIRMED,
	OUTCOME_NON_ACTIONABLE,
)
from module_4_api_ui.backend.services.severity_policy import assign_priority, assign_severity
from shared.models.audit_finding import AuditEngineResult, DetectedEvidence, DetectedFinding


STUB_RULE_PACK_VERSION = "stub-2026.08.1"

# Statuses that represent an still-open clinical state. A record left in one of these
# long past its timestamp is what "stale" means for the purposes of FR-004.
OPEN_STATUS_VALUES = frozenset(
	{"active", "in-progress", "on-hold", "draft", "planned", "confirmed", "scheduled"}
)

# Statuses that mean a request or event is no longer live.
CLOSED_STATUS_VALUES = frozenset(
	{"stopped", "cancelled", "completed", "entered-in-error", "revoked", "finished"}
)

UNRESOLVED_REFERENCE_STATES = frozenset({"missing", "unresolved", "invalid"})

DEFAULT_STALE_AFTER_DAYS = 365


def _parse_timestamp(value: Any) -> datetime | None:
	if not isinstance(value, str) or not value:
		return None
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return None
	if parsed.tzinfo is None:
		parsed = parsed.replace(tzinfo=timezone.utc)
	return parsed


def _primary_timestamp(resource: Mapping[str, Any]) -> datetime | None:
	timestamps = resource.get("timestamps") or {}
	if not isinstance(timestamps, Mapping):
		return None
	for value in timestamps.values():
		parsed = _parse_timestamp(value)
		if parsed is not None:
			return parsed
	return None


def _reference_target(resource: Mapping[str, Any], field: str) -> str | None:
	references = resource.get("references") or {}
	if not isinstance(references, Mapping):
		return None
	raw = references.get(field)
	if isinstance(raw, str) and raw:
		return raw.split("/")[-1]
	if isinstance(raw, Mapping):
		target = raw.get("target_id") or raw.get("reference")
		if isinstance(target, str) and target:
			return target.split("/")[-1]
	return None


def _evidence_for(resource: Mapping[str, Any], evidence_type: str) -> DetectedEvidence:
	return DetectedEvidence(
		evidence_type=evidence_type,
		record_external_id=str(resource.get("record_id")) if resource.get("record_id") else None,
		normalized_resource_id=resource.get("normalized_resource_id"),
		payload={
			"resource_type": resource.get("resource_type"),
			"family": resource.get("family"),
			"status": resource.get("status"),
			"status_state": resource.get("status_state"),
			"timestamps": resource.get("timestamps") or {},
			"references": resource.get("references") or {},
			"incomplete_fields": list(resource.get("incomplete_fields") or []),
			"unresolved_links": list(resource.get("unresolved_links") or []),
		},
	)


def _outcome_for(
	resources: Sequence[Mapping[str, Any]],
	confirmed_outcome: str,
	finding_type: str,
) -> str:
	"""Decide whether a finding is confirmed or blocked by incomplete data.

	UC-002 extension 2a: incomplete data must not be mistaken for a confirmed
	contradiction. The finding is still emitted — deterministic records are never
	suppressed — but it is marked so triage can block acceptance.

	The test is deliberately ``incomplete_fields`` (status and timestamp — the fields the
	rules actually reason over) rather than module 1's broader ``rule_ready`` flag.
	``rule_ready`` is also false whenever any reference is unresolved, and in a
	resource-scoped FHIR batch ``subject`` always points at a Patient that was never in
	the batch. Keying off that would mark nearly every finding non-actionable and make
	triage meaningless.

	Relationship findings are exempt entirely: for a ``REL-*`` rule the unresolved link
	is the finding (FR-005), not a defect in the evidence supporting it.
	"""
	if finding_type == FINDING_TYPE_MISSING_RELATIONSHIP:
		return confirmed_outcome
	if any(resource.get("incomplete_fields") for resource in resources):
		return OUTCOME_NON_ACTIONABLE
	return confirmed_outcome


def _build_finding(
	rule_id: str,
	finding_type: str,
	summary: str,
	resources: Sequence[Mapping[str, Any]],
	confirmed_outcome: str,
	evidence_type: str = EVIDENCE_CONFLICTING_RECORD,
	rule_parameters: Dict[str, Any] | None = None,
) -> DetectedFinding:
	families = [str(resource.get("family") or resource.get("resource_type") or "") for resource in resources]
	outcome = _outcome_for(resources, confirmed_outcome, finding_type)
	severity = assign_severity(rule_id, families, outcome)
	priority = assign_priority(severity, outcome, len({family for family in families if family}))

	return DetectedFinding(
		rule_id=rule_id,
		finding_type=finding_type,
		severity=severity,
		priority=priority,
		summary=summary,
		audit_outcome=outcome,
		evidence=[_evidence_for(resource, evidence_type) for resource in resources],
		rule_parameters=rule_parameters or {},
	)


class StubAuditEngine:
	"""Deterministic placeholder implementing :class:`AuditEnginePort`."""

	def __init__(
		self,
		as_of: datetime | None = None,
		stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
	) -> None:
		self._as_of = as_of
		self._stale_after_days = stale_after_days

	@property
	def rule_pack_version(self) -> str:
		return STUB_RULE_PACK_VERSION

	@property
	def is_placeholder(self) -> bool:
		return True

	def _now(self) -> datetime:
		return self._as_of or datetime.now(timezone.utc)

	def evaluate_batch(
		self,
		resources: Sequence[Mapping[str, Any]],
		rule_pack: Mapping[str, Any],
	) -> AuditEngineResult:
		ordered = sorted(resources, key=lambda item: str(item.get("record_id") or ""))
		by_id = {str(item.get("record_id")): item for item in ordered if item.get("record_id")}
		stale_after_days = int(rule_pack.get("stale_after_days", self._stale_after_days))

		findings: List[DetectedFinding] = []
		skipped = 0

		for resource in ordered:
			findings.extend(self._contradiction_rules(resource, by_id))
			stale, was_skipped = self._stale_rule(resource, stale_after_days)
			findings.extend(stale)
			skipped += was_skipped
			findings.extend(self._timeline_rules(resource, by_id))
			findings.extend(self._relationship_rules(resource))

		return AuditEngineResult(
			rule_pack_version=self.rule_pack_version,
			findings=findings,
			evaluated_record_count=len(ordered),
			skipped_record_count=skipped,
		)

	def _contradiction_rules(
		self,
		resource: Mapping[str, Any],
		by_id: Mapping[str, Mapping[str, Any]],
	) -> List[DetectedFinding]:
		"""Cross-resource status contradictions (FR-003)."""
		findings: List[DetectedFinding] = []
		resource_type = str(resource.get("resource_type") or "")
		status = str(resource.get("status") or "").lower()

		# The BRD's headline example: an active CarePlan still pointing at a
		# medication request that has been stopped.
		if resource_type == "CarePlan" and status in OPEN_STATUS_VALUES:
			for field in ("basedOn", "activity", "encounter", "subject"):
				target_id = _reference_target(resource, field)
				target = by_id.get(target_id) if target_id else None
				if target is None:
					continue
				if str(target.get("resource_type") or "") != "MedicationRequest":
					continue
				if str(target.get("status") or "").lower() not in CLOSED_STATUS_VALUES:
					continue
				findings.append(
					_build_finding(
						rule_id="CONTRA-CAREPLAN-MEDREQ-STATUS",
						finding_type=FINDING_TYPE_CONTRADICTION,
						summary=(
							f"Active CarePlan {resource.get('record_id')} references "
							f"MedicationRequest {target.get('record_id')} whose status is "
							f"'{target.get('status')}'."
						),
						resources=[resource, target],
						confirmed_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
						rule_parameters={"reference_field": field},
					)
				)

		if resource_type == "Condition" and status in OPEN_STATUS_VALUES:
			target_id = _reference_target(resource, "encounter")
			target = by_id.get(target_id) if target_id else None
			if target is not None and str(target.get("resource_type") or "") == "Encounter":
				if str(target.get("status") or "").lower() in {"cancelled", "entered-in-error"}:
					findings.append(
						_build_finding(
							rule_id="CONTRA-CONDITION-ENCOUNTER-STATE",
							finding_type=FINDING_TYPE_CONTRADICTION,
							summary=(
								f"Active Condition {resource.get('record_id')} is linked to "
								f"Encounter {target.get('record_id')} with status "
								f"'{target.get('status')}'."
							),
							resources=[resource, target],
							confirmed_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
							rule_parameters={"reference_field": "encounter"},
						)
					)

		return findings

	def _stale_rule(
		self,
		resource: Mapping[str, Any],
		stale_after_days: int,
	) -> tuple[List[DetectedFinding], int]:
		"""Open states left untouched past the rule-pack threshold (FR-004)."""
		status = str(resource.get("status") or "").lower()
		if status not in OPEN_STATUS_VALUES:
			return [], 0

		timestamp = _primary_timestamp(resource)
		if timestamp is None:
			return [], 1

		age_days = (self._now() - timestamp).days
		if age_days <= stale_after_days:
			return [], 0

		return (
			[
				_build_finding(
					rule_id="STALE-STATUS-OPEN",
					finding_type=FINDING_TYPE_STALE_STATE,
					summary=(
						f"{resource.get('resource_type')} {resource.get('record_id')} has been "
						f"'{resource.get('status')}' for {age_days} days, exceeding the "
						f"{stale_after_days}-day rule-pack threshold."
					),
					resources=[resource],
					confirmed_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
					rule_parameters={"age_days": age_days, "stale_after_days": stale_after_days},
				)
			],
			0,
		)

	def _timeline_rules(
		self,
		resource: Mapping[str, Any],
		by_id: Mapping[str, Mapping[str, Any]],
	) -> List[DetectedFinding]:
		"""Impossible event ordering (FR-004)."""
		findings: List[DetectedFinding] = []
		timestamp = _primary_timestamp(resource)
		if timestamp is None:
			return findings

		if timestamp > self._now():
			findings.append(
				_build_finding(
					rule_id="TIMELINE-FUTURE-EVENT",
					finding_type=FINDING_TYPE_TIMELINE_VIOLATION,
					summary=(
						f"{resource.get('resource_type')} {resource.get('record_id')} carries a "
						f"timestamp in the future ({timestamp.isoformat()})."
					),
					resources=[resource],
					confirmed_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
					rule_parameters={"observed_at": timestamp.isoformat()},
				)
			)

		encounter_id = _reference_target(resource, "encounter")
		encounter = by_id.get(encounter_id) if encounter_id else None
		if encounter is not None:
			encounter_timestamp = _primary_timestamp(encounter)
			if encounter_timestamp is not None and timestamp < encounter_timestamp:
				findings.append(
					_build_finding(
						rule_id="TIMELINE-EVENT-PRECEDES-ENCOUNTER",
						finding_type=FINDING_TYPE_TIMELINE_VIOLATION,
						summary=(
							f"{resource.get('resource_type')} {resource.get('record_id')} is dated "
							f"{timestamp.isoformat()}, before its Encounter "
							f"{encounter.get('record_id')} at {encounter_timestamp.isoformat()}."
						),
						resources=[resource, encounter],
						confirmed_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
						rule_parameters={"reference_field": "encounter"},
					)
				)

		return findings

	def _relationship_rules(self, resource: Mapping[str, Any]) -> List[DetectedFinding]:
		"""Rule-expected relationships that are absent or unresolved (FR-005).

		Reuses ``expected_relationships_for`` from module 2 so the rule IDs match the
		``REL-{TYPE}-{FIELD}`` signals module 1 has already persisted. FR-005 is
		explicit that gaps are flagged only where a rule expects the relationship —
		never as universal clinical truth.
		"""
		findings: List[DetectedFinding] = []
		resource_type = str(resource.get("resource_type") or "")
		references = resource.get("references") or {}

		for field in expected_relationships_for(resource_type):
			raw = references.get(field) if isinstance(references, Mapping) else None
			state = None
			present = False
			if isinstance(raw, Mapping):
				state = str(raw.get("state") or "")
				present = bool(raw.get("reference") or raw.get("target_id"))
			elif isinstance(raw, str):
				present = bool(raw)

			if present and state not in UNRESOLVED_REFERENCE_STATES:
				continue

			rule_id = f"REL-{resource_type.upper()}-{field.upper()}"
			findings.append(
				_build_finding(
					rule_id=rule_id,
					finding_type=FINDING_TYPE_MISSING_RELATIONSHIP,
					summary=(
						f"{resource_type} {resource.get('record_id')} is missing the rule-expected "
						f"'{field}' relationship."
					),
					resources=[resource],
					confirmed_outcome=OUTCOME_GAP_CONFIRMED,
					evidence_type=EVIDENCE_GOVERNED_SIGNAL,
					rule_parameters={"relationship_field": field, "reference_state": state},
				)
			)

		return findings
