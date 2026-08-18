"""Immutable Finding model for audit findings.

Represents a contradiction finding emitted by a rule. Once created,
findings are sealed (immutable) and cannot be modified, ensuring
reproducibility and compliance with audit requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Finding:
    """Immutable contradiction finding.

    Represents a single finding emitted by a rule. Frozen dataclass
    ensures no modification after creation (sealed findings).

    Attributes:
        rule_id: ID of the rule that detected the finding
        severity: Severity level (info, warning, critical)
        category: Finding category (diagnosis, medication, timeline, etc.)
        evidence: List of supporting evidence items (mappings of evidence data)
        narrative: Human-readable description of the finding
        metadata: Additional finding metadata (source, timestamp, etc.)
        status: Finding status (active, resolved, archived)

    Examples:
        >>> finding = Finding(
        ...     rule_id="RULE-COND-001",
        ...     severity="warning",
        ...     category="diagnosis",
        ...     evidence=[{"field": "condition", "value": "active"}],
        ...     narrative="Conflicting diagnosis found",
        ...     metadata={"detected_at": "2026-08-17T12:00:00Z"},
        ...     status="active"
        ... )
        >>> # Attempting to modify raises error
        >>> finding.severity = "critical"  # TypeError
        Traceback (most recent call last):
            ...
        dataclasses.FrozenInstanceError: cannot assign to field 'severity'
    """

    rule_id: str
    severity: str  # info, warning, critical
    category: str  # diagnosis, medication, timeline, etc.
    evidence: tuple[Mapping[str, Any], ...] = ()
    narrative: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, resolved, archived
    finding_id: str = ""
    rule_version: str = "1.0.0"
    batch_run_id: str = ""
    timestamp_utc: str = ""
    audit_outcome: str = "FLAGGED"
    severity_tier: str = "LOW"
    resource_references: tuple[str, ...] = ()
    conflicting_fields: tuple[str, ...] = ()
    field_values: Mapping[str, Any] = field(default_factory=dict)
    evidence_completeness_pct: float = 0.0
    input_snapshot_hash: str = ""
    output_finding_hash: str = ""
    rule_logic_summary: str = ""

    def __post_init__(self) -> None:
        """Validate finding after initialization.

        Raises:
            ValueError: If required fields missing or invalid
        """
        if not self.rule_id:
            raise ValueError("rule_id cannot be empty")

        if self.severity not in ("info", "warning", "critical"):
            raise ValueError(
                f"Invalid severity '{self.severity}': "
                "must be info, warning, or critical"
            )

        if self.status not in ("active", "resolved", "archived"):
            raise ValueError(
                f"Invalid status '{self.status}': "
                "must be active, resolved, or archived"
            )

        if not 0.0 <= self.evidence_completeness_pct <= 100.0:
            raise ValueError("evidence_completeness_pct must be between 0 and 100")

        if self.severity_tier not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            raise ValueError("severity_tier must be CRITICAL, HIGH, MEDIUM, or LOW")

    def as_dict(self) -> dict[str, Any]:
        """Serialize finding to dictionary.

        Returns:
            dict[str, Any]: Finding as dictionary with evidence list
        """
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "evidence": list(self.evidence),
            "narrative": self.narrative,
            "metadata": dict(self.metadata),
            "status": self.status,
            "finding_id": self.finding_id,
            "rule_version": self.rule_version,
            "batch_run_id": self.batch_run_id,
            "timestamp_utc": self.timestamp_utc,
            "audit_outcome": self.audit_outcome,
            "severity_tier": self.severity_tier,
            "resource_references": list(self.resource_references),
            "conflicting_fields": list(self.conflicting_fields),
            "field_values": dict(self.field_values),
            "evidence_completeness_pct": self.evidence_completeness_pct,
            "input_snapshot_hash": self.input_snapshot_hash,
            "output_finding_hash": self.output_finding_hash,
            "rule_logic_summary": self.rule_logic_summary,
        }
