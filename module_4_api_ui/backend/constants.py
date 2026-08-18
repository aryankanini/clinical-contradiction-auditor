from __future__ import annotations

"""Domain vocabulary for the module 4 API.

The database columns backing these values are free-form strings
(``FindingRow.status`` is ``String(32)``), so this module is the single place the
allowed values are defined. Every value here is <= 32 characters.
"""

from typing import Dict, FrozenSet, Literal, Tuple


Role = Literal["steward", "analyst", "compliance"]

ROLES: FrozenSet[str] = frozenset({"steward", "analyst", "compliance"})

# --- Findings -------------------------------------------------------------

STATUS_NEW = "new"
STATUS_UNDER_REVIEW = "under_review"
STATUS_ACCEPTED = "accepted"
STATUS_DEFERRED = "deferred"
STATUS_ESCALATED = "escalated"
STATUS_DISPUTED = "disputed"
STATUS_NON_ACTIONABLE = "non_actionable"
STATUS_IN_REMEDIATION = "in_remediation"
STATUS_REMEDIATED = "remediated"
STATUS_CLOSED = "closed"
STATUS_CLOSED_NO_ACTION = "closed_no_action"

TERMINAL_STATUSES: FrozenSet[str] = frozenset({STATUS_CLOSED, STATUS_CLOSED_NO_ACTION})

SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

SEVERITIES: Tuple[str, ...] = (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW)

SEVERITY_RANK: Dict[str, int] = {
	SEVERITY_CRITICAL: 4,
	SEVERITY_HIGH: 3,
	SEVERITY_MEDIUM: 2,
	SEVERITY_LOW: 1,
}

PRIORITY_P1 = "p1"
PRIORITY_P2 = "p2"
PRIORITY_P3 = "p3"
PRIORITY_P4 = "p4"

PRIORITIES: Tuple[str, ...] = (PRIORITY_P1, PRIORITY_P2, PRIORITY_P3, PRIORITY_P4)

PRIORITY_RANK: Dict[str, int] = {
	PRIORITY_P1: 1,
	PRIORITY_P2: 2,
	PRIORITY_P3: 3,
	PRIORITY_P4: 4,
}

# Finding types produced by the deterministic engine (FR-003/004/005).
FINDING_TYPE_CONTRADICTION = "contradiction"
FINDING_TYPE_STALE_STATE = "stale_state"
FINDING_TYPE_TIMELINE_VIOLATION = "timeline_violation"
FINDING_TYPE_MISSING_RELATIONSHIP = "missing_relationship"

FINDING_TYPES: Tuple[str, ...] = (
	FINDING_TYPE_CONTRADICTION,
	FINDING_TYPE_STALE_STATE,
	FINDING_TYPE_TIMELINE_VIOLATION,
	FINDING_TYPE_MISSING_RELATIONSHIP,
)

# Audit outcomes (FR-006). ``non_actionable_incomplete_data`` is UC-002 extension 2a:
# the finding is still recorded, but incomplete transparency blocks acceptance.
OUTCOME_CONTRADICTION_CONFIRMED = "contradiction_confirmed"
OUTCOME_GAP_CONFIRMED = "gap_confirmed"
OUTCOME_NON_ACTIONABLE = "non_actionable_incomplete_data"

# --- Evidence -------------------------------------------------------------
# ``finding_evidence`` has no dedicated table for approved resolutions or compliance
# sign-off, so ``evidence_type`` is namespaced. Engine-produced types carry a
# ``normalized_resource_id``; service-produced types leave it NULL.
EVIDENCE_CONFLICTING_RECORD = "conflicting_record"
EVIDENCE_GOVERNED_SIGNAL = "governed_signal"
EVIDENCE_RULE_CONTEXT = "rule_context"
EVIDENCE_APPROVED_RESOLUTION = "approved_resolution"
EVIDENCE_COMPLIANCE_VERIFICATION = "compliance_verification"

ENGINE_EVIDENCE_TYPES: FrozenSet[str] = frozenset(
	{EVIDENCE_CONFLICTING_RECORD, EVIDENCE_GOVERNED_SIGNAL, EVIDENCE_RULE_CONTEXT}
)

# --- Audit runs -----------------------------------------------------------

RUN_QUEUED = "queued"
RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"

ACTIVE_RUN_STATUSES: FrozenSet[str] = frozenset({RUN_QUEUED, RUN_RUNNING})

# --- Rule packs -----------------------------------------------------------

RULE_PACK_PUBLISHED = "published"
RULE_PACK_DRAFT = "draft"
RULE_PACK_RETIRED = "retired"

# --- Triage ---------------------------------------------------------------

TRIAGE_ACCEPT = "accept"
TRIAGE_DEFER = "defer"
TRIAGE_ESCALATE = "escalate"
TRIAGE_DISPUTE = "dispute"

TRIAGE_TARGET_STATUS: Dict[str, str] = {
	TRIAGE_ACCEPT: STATUS_ACCEPTED,
	TRIAGE_DEFER: STATUS_DEFERRED,
	TRIAGE_ESCALATE: STATUS_ESCALATED,
	TRIAGE_DISPUTE: STATUS_DISPUTED,
}

SYSTEM_ACTOR = "system"
