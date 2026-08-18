from __future__ import annotations

from typing import Any, Mapping

import pytest

from module_2_audit_engine.rules.timeline_rules import RuleLifecycle001, RuleStale001, RuleTemporal001


def resource(**overrides: Any) -> Mapping[str, Any]:
	base: dict[str, Any] = {"resourceType": "Condition", "id": "condition-1", "status": "active", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}}
	base.update(overrides)
	return base


@pytest.mark.parametrize(("last_updated", "expected"), [("2020-08-16T00:00:00Z", 1), ("2024-08-17T00:00:00Z", 0), (None, 0)])
def test_stale_state_handles_old_recent_and_missing_dates(last_updated: str | None, expected: int) -> None:
	assert len(RuleStale001().execute([resource(lastUpdated=last_updated)])) == expected


def test_stale_threshold_is_configurable() -> None:
	assert RuleStale001(threshold_years=1).execute([resource(lastUpdated="2024-08-17T00:00:00Z")])


@pytest.mark.parametrize("payload", [
	{"onsetDateTime": "2026-01-01T00:00:00Z", "abatementDateTime": "2025-01-01T00:00:00Z"},
	{"period": {"start": "2026-03-08T03:00:00-04:00", "end": "2026-03-08T01:00:00-05:00"}},
	{"period": {"start": "2024-03-01T00:00:00Z", "end": "2024-02-29T00:00:00Z"}},
])
def test_temporal_ordering_detects_reversed_dates(payload: Mapping[str, Any]) -> None:
	assert RuleTemporal001().execute([resource(**payload)])


@pytest.mark.parametrize("payload", [
	{"onsetDateTime": "2024-02-29T00:00:00Z", "abatementDateTime": "2024-03-01T00:00:00Z"},
	{"period": {"start": "2026-11-01T01:00:00-04:00", "end": "2026-11-01T01:30:00-05:00"}},
	{"onsetDateTime": None, "abatementDateTime": None},
])
def test_temporal_ordering_accepts_valid_or_missing_dates(payload: Mapping[str, Any]) -> None:
	assert RuleTemporal001().execute([resource(**payload)]) == []


@pytest.mark.parametrize(("previous", "current", "expected"), [("cancelled", "active", 1), ("entered-in-error", "active", 1), ("active", "completed", 0), (None, "active", 0)])
def test_lifecycle_transition_validation(previous: str | None, current: str, expected: int) -> None:
	resources = [resource(status=current, meta={"auditReferenceDate": "2026-08-17T00:00:00Z", "previousStatus": previous})]
	assert len(RuleLifecycle001().execute(resources)) == expected