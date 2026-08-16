from __future__ import annotations

"""Audit-only safety text required by FR-011.

These strings are attached to every response surface that can carry model-generated
text. They are constants rather than free-form copy so the boundary is auditable and
cannot drift per endpoint.
"""


AUDIT_ONLY_NOTICE = (
	"Audit-only output. This system does not diagnose, prescribe, or alter clinical intent. "
	"Findings describe data-integrity conditions established by deterministic rules."
)

AI_AUDIT_ONLY_DISCLAIMER = (
	"AI-generated explanation. Non-diagnostic and non-prescriptive. The contradiction was "
	"established by deterministic rule evaluation; AI text provides explanation and confidence "
	"context only and does not change the finding status. Human review is required."
)

RESOLUTION_AUDIT_ONLY_NOTE = (
	"This draft is non-diagnostic and requires human review before any action is taken."
)
