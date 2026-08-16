from __future__ import annotations

"""Severity and triage-priority assignment (FR-008).

FR-008 requires severity and priority to come from "predefined rule-based criteria".
Everything here is therefore a pure function over lookup tables — no AI, no wall clock,
no randomness — so an auditor can reproduce any assignment by hand.
"""

from typing import Dict, Sequence

from module_4_api_ui.backend.constants import (
	OUTCOME_NON_ACTIONABLE,
	PRIORITY_P1,
	PRIORITY_P4,
	PRIORITY_RANK,
	SEVERITY_HIGH,
	SEVERITY_MEDIUM,
	SEVERITY_RANK,
)


# Base severity per rule family. Rule IDs are matched by prefix so the parameterised
# relationship rules (REL-CONDITION-ENCOUNTER, ...) resolve without an entry each.
BASE_SEVERITY_BY_RULE_PREFIX: Dict[str, str] = {
	"CONTRA-CAREPLAN-MEDREQ-STATUS": "critical",
	"CONTRA-CONDITION-ENCOUNTER-STATE": "high",
	"CONTRA-": "high",
	"STALE-": "medium",
	"TIMELINE-EVENT-PRECEDES-ENCOUNTER": "high",
	"TIMELINE-FUTURE-EVENT": "medium",
	"TIMELINE-": "medium",
	"REL-": "medium",
}

# Resource families where a data-integrity gap carries more operational risk.
HIGH_RISK_FAMILIES: frozenset[str] = frozenset({"Condition", "Medication"})

PRIORITY_BY_SEVERITY: Dict[str, str] = {
	"critical": "p1",
	"high": "p2",
	"medium": "p3",
	"low": "p4",
}

_PRIORITY_BY_RANK: Dict[int, str] = {rank: value for value, rank in PRIORITY_RANK.items()}


def base_severity_for_rule(rule_id: str) -> str:
	"""Longest matching prefix wins, so specific rules override their family."""
	best_match = ""
	for prefix in BASE_SEVERITY_BY_RULE_PREFIX:
		if rule_id.startswith(prefix) and len(prefix) > len(best_match):
			best_match = prefix
	if not best_match:
		return SEVERITY_MEDIUM
	return BASE_SEVERITY_BY_RULE_PREFIX[best_match]


def assign_severity(rule_id: str, resource_families: Sequence[str], audit_outcome: str) -> str:
	"""Escalate one step when a high-risk family is involved."""
	severity = base_severity_for_rule(rule_id)

	if any(family in HIGH_RISK_FAMILIES for family in resource_families):
		if SEVERITY_RANK[severity] < SEVERITY_RANK[SEVERITY_HIGH]:
			severity = SEVERITY_HIGH

	return severity


def assign_priority(
	severity: str,
	audit_outcome: str,
	distinct_family_count: int,
) -> str:
	"""Map severity to priority, then apply two rule-defined adjustments.

	- Cross-resource findings move up one step: contradictions spanning two or more
	  resource families are the product's headline risk (BRD problems 1 and 4).
	- Non-actionable findings move down one step: incomplete data should not consume
	  steward attention ahead of confirmed contradictions (UC-002 extension 2a).
	"""
	rank = PRIORITY_RANK[PRIORITY_BY_SEVERITY[severity]]

	if distinct_family_count >= 2:
		rank -= 1
	if audit_outcome == OUTCOME_NON_ACTIONABLE:
		rank += 1

	rank = max(PRIORITY_RANK[PRIORITY_P1], min(PRIORITY_RANK[PRIORITY_P4], rank))
	return _PRIORITY_BY_RANK[rank]
