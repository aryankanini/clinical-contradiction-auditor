"""Deterministically hydrate raw rule output into immutable audit findings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any, Mapping

from module_2_audit_engine.models.finding import Finding


def _canonical_hash(value: object) -> str:
	payload = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_evidence(raw_finding: Mapping[str, Any], resources: list[Mapping[str, Any]], batch_run_id: str, timestamp_utc: str, rule_version: str = "1.0.0") -> Finding:
	"""Create a reproducible Finding from a raw rule result and its input snapshot."""
	evidence = raw_finding.get("evidence", [])
	items = evidence if isinstance(evidence, list) else []
	field_values = {str(item.get("field")): item.get("value") for item in items if isinstance(item, Mapping) and item.get("field") is not None}
	references = tuple(sorted({f"{resource.get('resourceType')}/{resource.get('id')}" for resource in resources if isinstance(resource.get("resourceType"), str) and isinstance(resource.get("id"), str)}))
	completeness = 100.0 if field_values and references else 0.0
	base = Finding(
		rule_id=str(raw_finding["rule_id"]), severity=str(raw_finding.get("severity", "warning")), category=str(raw_finding.get("category", "unknown")),
		evidence=tuple(items), narrative=str(raw_finding.get("narrative", "")), status=str(raw_finding.get("status", "active")),
		finding_id=_canonical_hash({"batch_run_id": batch_run_id, "rule_id": raw_finding["rule_id"], "raw_finding": raw_finding})[:32], rule_version=rule_version,
		batch_run_id=batch_run_id, timestamp_utc=timestamp_utc, resource_references=references, conflicting_fields=tuple(field_values), field_values=field_values,
		evidence_completeness_pct=completeness, input_snapshot_hash=_canonical_hash(resources),
	)
	return replace(base, output_finding_hash=_canonical_hash(base.as_dict()))