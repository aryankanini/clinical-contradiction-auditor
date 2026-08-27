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
	RuleEncounter001,
	RuleEncounter002,
	RuleObservation001,
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
from shared.models.audit_finding import AuditEngineResult, DetectedEvidence, DetectedFinding


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

	# Start from the untouched ingest payload so rules can read fields normalization
	# doesn't extract (e.g. Condition.code) — normalized fields below always win over it.
	raw_payload = record.get("raw_payload")
	resource: Dict[str, Any] = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}

	resource.update(
		{
			"resourceType": str(record.get("resource_type") or "Unknown"),
			"id": str(record.get("record_id") or "unknown"),
			"status": record.get("status"),
			"meta": {"auditReferenceDate": now.isoformat()},
		}
	)

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


# Maps rule IDs to their governed finding types. Rules not listed default to FINDING_TYPE_CONTRADICTION.
_RULE_ID_TO_FINDING_TYPE: Dict[str, str] = {
	"RULE-STALE-001": FINDING_TYPE_STALE_STATE,
	"RULE-MED-001": FINDING_TYPE_STALE_STATE,
	"RULE-LIFECYCLE-001": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-TEMPORAL-001": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-ENC-001": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-ENC-002": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-PROC-002": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-OBS-001": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-CARE-001": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-CARE-002": FINDING_TYPE_TIMELINE_VIOLATION,
	"RULE-MED-002": FINDING_TYPE_TIMELINE_VIOLATION,
}


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
		RuleCarePlan001,
		RuleCarePlan002,
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
		self._metadata_by_rule_id: Dict[str, RuleDefinition] = {}

		for rule_class in self._RULE_CLASSES:
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

	def _build_factory(self, stale_threshold_years: int) -> RuleFactory:
		"""Build a rule factory with the configured stale threshold."""
		# Dynamically create a configured RuleStale001 class so the pack's
		# stale_after_days parameter is honoured rather than defaulting to five years.
		class _ConfiguredStale(RuleStale001):
			def __init__(self) -> None:
				super().__init__(threshold_years=stale_threshold_years)

		factory = RuleFactory()
		for rule_class in self._RULE_CLASSES:
			if rule_class is RuleStale001:
				factory.register(_ConfiguredStale)
			else:
				factory.register(rule_class)
		return factory

	def _select_rule_ids(self, rule_pack: Mapping[str, Any]) -> List[str]:
		configured = rule_pack.get("rules")
		if configured is None:
			# No explicit rule list: run all registered rules.
			return sorted(self._metadata_by_rule_id)

		if not (isinstance(configured, Iterable) and not isinstance(configured, (str, bytes, Mapping))):
			return sorted(self._metadata_by_rule_id)

		# Explicit rule list (even if empty): honor it, respect enabled flag, reject unknown IDs.
		configured_ids: List[str] = []
		for item in configured:
			if isinstance(item, Mapping):
				candidate = item.get("rule_id")
				enabled = item.get("enabled", True)
			else:
				candidate = item
				enabled = True

			if not isinstance(candidate, str) or not candidate:
				continue

			if candidate not in self._metadata_by_rule_id:
				raise ValueError(f"Unknown rule ID in rule pack: {candidate!r}")

			if enabled:
				configured_ids.append(candidate)

		return sorted(set(configured_ids))

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

	def _governed_signal_findings(
		self, records: Sequence[Mapping[str, Any]]
	) -> List[DetectedFinding]:
		"""Translate governed relationship signals into missing_relationship findings (FR-005)."""
		findings: List[DetectedFinding] = []
		for record in records:
			signals = record.get("governed_signals") or []
			rule_ready = record.get("rule_ready", True)
			record_id = record.get("record_id")
			for signal_rule_id in signals:
				if not isinstance(signal_rule_id, str):
					continue
				outcome = OUTCOME_GAP_CONFIRMED if rule_ready else OUTCOME_NON_ACTIONABLE
				findings.append(
					DetectedFinding(
						rule_id=signal_rule_id,
						finding_type=FINDING_TYPE_MISSING_RELATIONSHIP,
						severity="medium",
						priority=_priority_for_severity("medium"),
						summary=(
							f"Record {record_id} has a missing governed relationship "
							f"flagged by {signal_rule_id}."
						),
						audit_outcome=outcome,
						evidence=[
							DetectedEvidence(
								evidence_type=EVIDENCE_GOVERNED_SIGNAL,
								record_external_id=str(record_id) if record_id else None,
								payload={"signal_rule_id": signal_rule_id},
							)
						],
						rule_parameters={"signal": signal_rule_id},
					)
				)
		return findings

	def _to_detected_finding(
		self,
		finding: Mapping[str, Any],
		rule_ready_by_id: Mapping[str, bool],
	) -> DetectedFinding:
		rule_id = str(finding.get("rule_id") or "UNKNOWN")
		# Derive finding type from governed rule metadata (rule ID), not category.
		finding_type = _RULE_ID_TO_FINDING_TYPE.get(rule_id, FINDING_TYPE_CONTRADICTION)
		severity = _normalize_severity(finding.get("severity") if isinstance(finding.get("severity"), str) else None)
		priority = _priority_for_severity(severity)
		summary = str(finding.get("narrative") or "Deterministic contradiction detected.")

		evidence_rows = finding.get("evidence")
		detected_evidence: List[DetectedEvidence] = []
		involved_record_ids: List[str] = []
		if isinstance(evidence_rows, list):
			for row in evidence_rows:
				if not isinstance(row, Mapping):
					continue
				rec_id = _extract_record_id(row)
				if rec_id:
					involved_record_ids.append(rec_id)
				detected_evidence.append(
					DetectedEvidence(
						evidence_type=EVIDENCE_CONFLICTING_RECORD,
						record_external_id=rec_id,
						payload={"field": row.get("field"), "value": row.get("value")},
					)
				)

		# Carry source readiness into outcome: if any involved record is not rule_ready,
		# mark as non_actionable_incomplete_data rather than contradiction_confirmed.
		if finding_type != FINDING_TYPE_MISSING_RELATIONSHIP and any(
			not rule_ready_by_id.get(rec_id, True) for rec_id in involved_record_ids
		):
			audit_outcome = OUTCOME_NON_ACTIONABLE
		else:
			audit_outcome = OUTCOME_CONTRADICTION_CONFIRMED

		return DetectedFinding(
			rule_id=rule_id,
			finding_type=finding_type,
			severity=severity,
			priority=priority,
			summary=summary,
			audit_outcome=audit_outcome,
			evidence=detected_evidence,
			rule_parameters={"finding_type": finding_type},
		)

	def evaluate_batch(
		self,
		resources: Sequence[Mapping[str, Any]],
		rule_pack: Mapping[str, Any],
	) -> AuditEngineResult:
		now = self._now()
		ordered_inputs = sorted(resources, key=lambda item: str(item.get("record_id") or ""))
		normalized_resources = [_to_rule_resource(record, now) for record in ordered_inputs]

		# Build a map from record_id to rule_ready for outcome assignment.
		rule_ready_by_id: Dict[str, bool] = {
			str(record.get("record_id") or ""): bool(record.get("rule_ready", True))
			for record in ordered_inputs
		}

		# Apply the pack's stale threshold to RuleStale001 (defaults to 5 years when absent).
		stale_after_days = int(rule_pack.get("stale_after_days") or 365 * 5)
		stale_threshold_years = max(1, stale_after_days // 365)
		factory = self._build_factory(stale_threshold_years)

		pack = self._build_rule_pack(rule_pack)
		orchestrator = RuleOrchestrator(factory=factory)
		raw_findings = orchestrator.execute(rule_pack=pack, resources=normalized_resources)

		# Rule execution failures must fail the audit run, not become domain findings.
		error_findings = [f for f in raw_findings if f.get("status") == "FAILED"]
		if error_findings:
			failed_rule_ids = ", ".join(str(f.get("rule_id", "UNKNOWN")) for f in error_findings)
			raise RuntimeError(f"Rule execution failed for rule(s): {failed_rule_ids}")

		detected_findings = [
			self._to_detected_finding(finding, rule_ready_by_id) for finding in raw_findings
		]

		# Add missing_relationship findings produced from governed signals (FR-005).
		detected_findings.extend(self._governed_signal_findings(ordered_inputs))

		return AuditEngineResult(
			rule_pack_version=pack.metadata.version,
			findings=detected_findings,
			evaluated_record_count=len(ordered_inputs),
			skipped_record_count=0,
		)
