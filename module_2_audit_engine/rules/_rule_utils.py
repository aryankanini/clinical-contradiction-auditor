"""Read-only helpers shared by deterministic FHIR contradiction rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


def resources_of_type(resources: list[Mapping[str, Any]], resource_type: str) -> list[Mapping[str, Any]]:
	return [resource for resource in resources if resource.get("resourceType") == resource_type]


def string_at(resource: Mapping[str, Any], *path: str) -> str | None:
	value: Any = resource
	for key in path:
		if not isinstance(value, Mapping):
			return None
		value = value.get(key)
	return value if isinstance(value, str) and value else None


def status(resource: Mapping[str, Any]) -> str | None:
	value = resource.get("status")
	if isinstance(value, str):
		return value.lower()
	clinical_status = resource.get("clinicalStatus")
	if isinstance(clinical_status, Mapping):
		text = clinical_status.get("text")
		if isinstance(text, str) and text:
			return text.lower()
		coding = clinical_status.get("coding")
		if isinstance(coding, list):
			for code in coding:
				if isinstance(code, Mapping):
					code_value = code.get("code")
					if isinstance(code_value, str):
						return code_value.lower()
	return None


def iso_datetime(value: object) -> datetime | None:
	if not isinstance(value, str) or not value:
		return None
	try:
		return datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return None


def reference_date(resource: Mapping[str, Any]) -> datetime | None:
	meta = resource.get("meta")
	if not isinstance(meta, Mapping):
		return None
	return iso_datetime(meta.get("auditReferenceDate"))


def resource_id(resource: Mapping[str, Any]) -> str:
	value = resource.get("id")
	return value if isinstance(value, str) and value else "unknown"


def finding(
	rule_id: str,
	severity: str,
	category: str,
	narrative: str,
	evidence: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
	return {
		"rule_id": rule_id,
		"severity": severity,
		"category": category,
		"narrative": narrative,
		"evidence": evidence,
		"status": "active",
	}