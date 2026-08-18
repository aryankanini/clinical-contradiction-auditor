from __future__ import annotations

from module_2_audit_engine.rules.timeline_rules import RuleLifecycle001, RuleStale001, RuleTemporal001


def test_timeline_pipeline_emits_all_rule_types() -> None:
	resources = [{"resourceType": "Condition", "id": "condition-1", "status": "active", "lastUpdated": "2020-01-01T00:00:00Z", "onsetDateTime": "2026-01-01T00:00:00Z", "abatementDateTime": "2025-01-01T00:00:00Z", "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z", "previousStatus": "cancelled"}}]
	findings = [finding for rule in (RuleStale001(), RuleTemporal001(), RuleLifecycle001()) for finding in rule.execute(resources)]

	assert {finding["rule_id"] for finding in findings} == {"RULE-STALE-001", "RULE-TEMPORAL-001", "RULE-LIFECYCLE-001"}


def test_timeline_pipeline_is_deterministic() -> None:
	resources = [{"resourceType": "Encounter", "id": "encounter-1", "status": "active", "period": {"start": "2026-02-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"}, "meta": {"auditReferenceDate": "2026-08-17T00:00:00Z"}}]
	rule = RuleTemporal001()

	assert rule.execute(resources) == rule.execute(resources)