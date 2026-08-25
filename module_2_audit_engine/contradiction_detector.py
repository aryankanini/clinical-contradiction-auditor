from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from module_2_audit_engine.deterministic.orchestrator import RuleOrchestrator
from module_2_audit_engine.deterministic.rule_interface import RuleFactory, RuleInterface
from module_2_audit_engine.models.rule_pack import RuleDefinition, RulePack, RulePackMetadata
from module_2_audit_engine.rules.diagnosis_rules import (
	RuleCondition001,
	RuleCondition002,
	RuleCondition003,
	RuleCondition004,
)
from module_2_audit_engine.rules.encounter_rules import (
	RuleCarePlan001,
	RuleCarePlan002,
	RuleCarePlan003,
	RuleEncounter001,
	RuleEncounter002,
	RuleObservation001,
	RuleObservation002,
	RuleProcedure001,
	RuleProcedure002,
)
from module_2_audit_engine.rules.medication_rules import (
	RuleMedication001,
	RuleMedication002,
	RuleMedication003,
	RuleMedication004,
	RuleMedication005,
)
from module_2_audit_engine.rules.timeline_rules import RuleLifecycle001, RuleStale001, RuleTemporal001
from shared.models.audit_finding import AuditEngineResult, DetectedEvidence, DetectedFinding


FINDING_TYPE_CONTRADICTION = "contradiction"
FINDING_TYPE_STALE_STATE = "stale_state"
FINDING_TYPE_TIMELINE_VIOLATION = "timeline_violation"

OUTCOME_CONTRADICTION_CONFIRMED = "contradiction_confirmed"

EVIDENCE_CONFLICTING_RECORD = "conflicting_record"


def _normalize_severity(raw: str | None) -> str:
	value = (raw or "").strip().lower()
	if value == "critical":
		return "critical"
	if value == "warning":
		return "medium"
	if value == "info":
		return "low"
	return "low"


def _priority_for_severity(severity: str) -> str:
	if severity == "critical":
		return "p1"
	if severity == "high":
		return "p2"
	if severity == "medium":
		return "p3"
	return "p4"


def _finding_type_for_category(category: str | None) -> str:
	if (category or "").strip().lower() == "timeline":
		return FINDING_TYPE_TIMELINE_VIOLATION
	return FINDING_TYPE_CONTRADICTION


def _extract_record_id(evidence_item: Mapping[str, Any]) -> str | None:
	field_name = str(evidence_item.get("field") or "")
	if not field_name.lower().endswith(".id"):
		return None
	value = evidence_item.get("value")
	if isinstance(value, str) and value:
		return value
	return None


def _first_timestamp(timestamps: Mapping[str, Any]) -> str | None:
	for value in timestamps.values():
		if isinstance(value, str) and value:
			return value
	return None


def _apply_timestamp_fields(resource: Dict[str, Any], timestamps: Mapping[str, Any]) -> None:
	period: Dict[str, Any] = {}
	effective_period: Dict[str, Any] = {}
	performed_period: Dict[str, Any] = {}

	for key, value in timestamps.items():
		if not isinstance(value, str) or not value:
			continue

		if key in {"onsetDateTime", "abatementDateTime", "effectiveDateTime", "performedDateTime", "lastUpdated"}:
			resource[key] = value
			continue

		if key == "period.start":
			period["start"] = value
			continue
		if key == "period.end":
			period["end"] = value
			continue

		if key == "effectivePeriod.start":
			effective_period["start"] = value
			continue
		if key == "effectivePeriod.end":
			effective_period["end"] = value
			continue

		if key == "performedPeriod.start":
			performed_period["start"] = value
			continue
		if key == "performedPeriod.end":
			performed_period["end"] = value
			continue

	if period:
		resource["period"] = period
	if effective_period:
		resource["effectivePeriod"] = effective_period
	if performed_period:
		resource["performedPeriod"] = performed_period


def _to_rule_resource(record: Mapping[str, Any], now: datetime) -> Dict[str, Any]:
	timestamps_raw = record.get("timestamps")
	timestamps: Mapping[str, Any] = timestamps_raw if isinstance(timestamps_raw, Mapping) else {}

	resource: Dict[str, Any] = {
		"resourceType": str(record.get("resource_type") or "Unknown"),
		"id": str(record.get("record_id") or "unknown"),
		"status": record.get("status"),
		"meta": {"auditReferenceDate": now.isoformat()},
	}

	_apply_timestamp_fields(resource, timestamps)

	if "lastUpdated" not in resource:
		fallback_last_updated = _first_timestamp(timestamps)
		if fallback_last_updated:
			resource["lastUpdated"] = fallback_last_updated

	references_raw = record.get("references")
	if isinstance(references_raw, Mapping):
		for key, value in references_raw.items():
			resource[str(key)] = value

	return resource


class ContradictionDetector:
	"""Deterministic module 2 engine that satisfies module 4's AuditEnginePort."""

	_RULE_CLASSES: tuple[type[RuleInterface], ...] = (
		RuleCondition001,
		RuleCondition002,
		RuleCondition003,
		RuleCondition004,
		RuleEncounter001,
		RuleEncounter002,
		RuleProcedure001,
		RuleProcedure002,
		RuleObservation001,
		RuleObservation002,
		RuleCarePlan001,
		RuleCarePlan002,
		RuleCarePlan003,
		RuleMedication001,
		RuleMedication002,
		RuleMedication003,
		RuleMedication004,
		RuleMedication005,
		RuleLifecycle001,
		RuleTemporal001,
		RuleStale001,
	)

	def __init__(self, as_of: datetime | None = None) -> None:
		self._as_of = as_of
		self._factory = RuleFactory()
		self._metadata_by_rule_id: Dict[str, RuleDefinition] = {}

		for rule_class in self._RULE_CLASSES:
			self._factory.register(rule_class)
			metadata = rule_class().metadata
			self._metadata_by_rule_id[metadata.rule_id] = RuleDefinition(
				rule_id=metadata.rule_id,
				version=metadata.version,
				name=metadata.name,
				description=metadata.description,
				category=metadata.category,
				enabled=True,
			)

	@property
	def rule_pack_version(self) -> str:
		return "2.0.0"

	@property
	def is_placeholder(self) -> bool:
		return False

	def _now(self) -> datetime:
		return self._as_of or datetime.now(timezone.utc)

	def _select_rule_ids(self, rule_pack: Mapping[str, Any]) -> List[str]:
		configured = rule_pack.get("rules")
		if isinstance(configured, Iterable) and not isinstance(configured, (str, bytes, Mapping)):
			configured_ids: List[str] = []
			for item in configured:
				if isinstance(item, Mapping):
					candidate = item.get("rule_id")
				else:
					candidate = item
				if isinstance(candidate, str) and candidate in self._metadata_by_rule_id:
					configured_ids.append(candidate)
			if configured_ids:
				return sorted(set(configured_ids))

		return sorted(self._metadata_by_rule_id)

	def _build_rule_pack(self, rule_pack: Mapping[str, Any]) -> RulePack:
		pack_version = str(rule_pack.get("version") or self.rule_pack_version)
		pack_id = str(rule_pack.get("rule_pack_id") or rule_pack.get("source") or "module2-default-pack")
		selected_rule_ids = self._select_rule_ids(rule_pack)

		return RulePack(
			metadata=RulePackMetadata(
				pack_id=pack_id,
				version=pack_version,
				created_at=self._now(),
				description="Runtime rule pack synthesized for deterministic execution.",
				author="module_2_audit_engine",
				organization="clinical-contradiction-auditor",
			),
			rules=[self._metadata_by_rule_id[rule_id] for rule_id in selected_rule_ids],
		)

	def _to_detected_finding(
		self,
		finding: Mapping[str, Any],
		category_by_rule_id: Mapping[str, str],
	) -> DetectedFinding:
		rule_id = str(finding.get("rule_id") or "UNKNOWN")
		category = category_by_rule_id.get(rule_id)
		severity = _normalize_severity(finding.get("severity") if isinstance(finding.get("severity"), str) else None)
		priority = _priority_for_severity(severity)
		summary = str(finding.get("narrative") or "Deterministic contradiction detected.")

		evidence_rows = finding.get("evidence")
		detected_evidence: List[DetectedEvidence] = []
		if isinstance(evidence_rows, list):
			for row in evidence_rows:
				if not isinstance(row, Mapping):
					continue
				detected_evidence.append(
					DetectedEvidence(
						evidence_type=EVIDENCE_CONFLICTING_RECORD,
						record_external_id=_extract_record_id(row),
						payload={"field": row.get("field"), "value": row.get("value")},
					)
				)

		return DetectedFinding(
			rule_id=rule_id,
			finding_type=_finding_type_for_category(category),
			severity=severity,
			priority=priority,
			summary=summary,
			audit_outcome=OUTCOME_CONTRADICTION_CONFIRMED,
			evidence=detected_evidence,
			rule_parameters={"category": category or "unknown"},
		)

	def evaluate_batch(
		self,
		resources: Sequence[Mapping[str, Any]],
		rule_pack: Mapping[str, Any],
	) -> AuditEngineResult:
		now = self._now()
		ordered_inputs = sorted(resources, key=lambda item: str(item.get("record_id") or ""))
		normalized_resources = [_to_rule_resource(record, now) for record in ordered_inputs]

		pack = self._build_rule_pack(rule_pack)
		orchestrator = RuleOrchestrator(factory=self._factory)
		raw_findings = orchestrator.execute(rule_pack=pack, resources=normalized_resources)

		category_by_rule_id = {
			rule_id: definition.category for rule_id, definition in pack.rule_id_to_definition.items()
		}
		detected_findings = [
			self._to_detected_finding(finding, category_by_rule_id) for finding in raw_findings
		]

		return AuditEngineResult(
			rule_pack_version=pack.metadata.version,
			findings=detected_findings,
			evaluated_record_count=len(ordered_inputs),
			skipped_record_count=0,
		)
