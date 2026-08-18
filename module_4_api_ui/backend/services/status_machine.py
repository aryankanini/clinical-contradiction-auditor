from __future__ import annotations

"""Finding lifecycle transitions (FR-010).

This module is pure: tables plus guard functions, no session and no I/O. Every mutator
in the service layer routes through :func:`assert_transition_allowed`, so the status
column and ``finding_status_history`` can never disagree about what is legal.
"""

from typing import Dict, FrozenSet, List, Sequence

from module_4_api_ui.backend.constants import (
	STATUS_ACCEPTED,
	STATUS_CLOSED,
	STATUS_CLOSED_NO_ACTION,
	STATUS_DEFERRED,
	STATUS_DISPUTED,
	STATUS_ESCALATED,
	STATUS_IN_REMEDIATION,
	STATUS_NEW,
	STATUS_NON_ACTIONABLE,
	STATUS_REMEDIATED,
	STATUS_UNDER_REVIEW,
	TERMINAL_STATUSES,
)
from module_4_api_ui.backend.errors import IllegalTransitionError


STATUS_TRANSITIONS: Dict[str, FrozenSet[str]] = {
	STATUS_NEW: frozenset({STATUS_UNDER_REVIEW, STATUS_NON_ACTIONABLE}),
	STATUS_UNDER_REVIEW: frozenset(
		{
			STATUS_ACCEPTED,
			STATUS_DEFERRED,
			STATUS_ESCALATED,
			STATUS_DISPUTED,
			STATUS_NON_ACTIONABLE,
		}
	),
	STATUS_ACCEPTED: frozenset({STATUS_IN_REMEDIATION, STATUS_ESCALATED, STATUS_DEFERRED}),
	STATUS_DEFERRED: frozenset({STATUS_UNDER_REVIEW, STATUS_CLOSED_NO_ACTION}),
	STATUS_DISPUTED: frozenset({STATUS_UNDER_REVIEW, STATUS_ACCEPTED, STATUS_CLOSED_NO_ACTION}),
	STATUS_ESCALATED: frozenset(
		{STATUS_UNDER_REVIEW, STATUS_ACCEPTED, STATUS_IN_REMEDIATION, STATUS_CLOSED_NO_ACTION}
	),
	STATUS_NON_ACTIONABLE: frozenset({STATUS_UNDER_REVIEW, STATUS_CLOSED_NO_ACTION}),
	STATUS_IN_REMEDIATION: frozenset({STATUS_REMEDIATED, STATUS_ESCALATED}),
	STATUS_REMEDIATED: frozenset({STATUS_CLOSED, STATUS_IN_REMEDIATION}),
	STATUS_CLOSED: frozenset(),
	STATUS_CLOSED_NO_ACTION: frozenset(),
}

# Which roles may drive a finding INTO each status.
ROLES_BY_TARGET_STATUS: Dict[str, FrozenSet[str]] = {
	STATUS_UNDER_REVIEW: frozenset({"steward", "analyst"}),
	STATUS_ACCEPTED: frozenset({"steward"}),
	STATUS_DEFERRED: frozenset({"steward"}),
	STATUS_ESCALATED: frozenset({"steward", "analyst"}),
	STATUS_DISPUTED: frozenset({"steward", "analyst"}),
	STATUS_NON_ACTIONABLE: frozenset({"steward", "analyst"}),
	STATUS_IN_REMEDIATION: frozenset({"steward"}),
	STATUS_REMEDIATED: frozenset({"steward", "analyst"}),
	STATUS_CLOSED: frozenset({"steward", "compliance"}),
	STATUS_CLOSED_NO_ACTION: frozenset({"steward", "compliance"}),
}

ALL_STATUSES: FrozenSet[str] = frozenset(STATUS_TRANSITIONS)
OPEN_STATUSES: FrozenSet[str] = ALL_STATUSES - TERMINAL_STATUSES


def is_terminal(status: str) -> bool:
	return status in TERMINAL_STATUSES


def legal_targets(status: str) -> FrozenSet[str]:
	return STATUS_TRANSITIONS.get(status, frozenset())


def allowed_transitions_for(
	status: str,
	role: str,
	*,
	has_approved_resolution: bool = False,
	has_assignment: bool = False,
) -> List[str]:
	"""Targets this role may pick right now, preconditions included.

	The UI drives its action menu from this list, so it can never offer an illegal
	action — but the server re-validates every request regardless.
	"""
	targets = []
	for target in sorted(legal_targets(status)):
		if role not in ROLES_BY_TARGET_STATUS.get(target, frozenset()):
			continue
		if target == STATUS_IN_REMEDIATION and not (has_approved_resolution and has_assignment):
			continue
		targets.append(target)
	return targets


def assert_transition_allowed(
	current_status: str,
	target_status: str,
	role: str,
	*,
	has_approved_resolution: bool = False,
	has_assignment: bool = False,
) -> None:
	"""Raise :class:`IllegalTransitionError` unless the move is permitted."""
	if target_status not in ALL_STATUSES:
		raise IllegalTransitionError(
			f"Unknown target status '{target_status}'.",
			context={"allowed_statuses": sorted(ALL_STATUSES)},
		)

	if is_terminal(current_status):
		raise IllegalTransitionError(
			f"Finding is already in terminal status '{current_status}'.",
			context={"current_status": current_status},
		)

	if target_status not in legal_targets(current_status):
		raise IllegalTransitionError(
			f"Cannot move a finding from '{current_status}' to '{target_status}'.",
			context={
				"current_status": current_status,
				"target_status": target_status,
				"allowed": sorted(legal_targets(current_status)),
			},
		)

	if role not in ROLES_BY_TARGET_STATUS.get(target_status, frozenset()):
		raise IllegalTransitionError(
			f"Role '{role}' may not move a finding to '{target_status}'.",
			context={
				"target_status": target_status,
				"required_roles": sorted(ROLES_BY_TARGET_STATUS.get(target_status, frozenset())),
			},
			code="forbidden_transition",
		)

	# FR-009: a finding may not enter remediation on AI output alone. Requiring both an
	# approved resolution and an owner assignment encodes "human approval before any
	# downstream resolution state change" structurally rather than by convention.
	if target_status == STATUS_IN_REMEDIATION:
		missing: List[str] = []
		if not has_approved_resolution:
			missing.append("approved_resolution")
		if not has_assignment:
			missing.append("assignment")
		if missing:
			raise IllegalTransitionError(
				"A finding requires an approved resolution and an owner assignment "
				"before remediation can begin.",
				context={"missing": missing},
				code="resolution_approval_required",
			)


def path_from(current_status: str, target_status: str) -> Sequence[str]:
	"""Return the implicit steps needed to reach ``target_status``.

	Triage acts on findings that are still ``new``; rather than reject that, the service
	walks ``new -> under_review -> <target>`` and writes a history row for each hop, so
	the "opened for review" event is never lost.
	"""
	if target_status in legal_targets(current_status):
		return (target_status,)
	if current_status == STATUS_NEW and target_status in legal_targets(STATUS_UNDER_REVIEW):
		return (STATUS_UNDER_REVIEW, target_status)
	return (target_status,)
