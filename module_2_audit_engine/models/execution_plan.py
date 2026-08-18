"""Execution plan schema for rule orchestration.

Defines the structure for rule execution plans with canonical ordering
and execution metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List
from uuid import uuid4


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable execution plan for rule execution.

    Attributes:
        plan_id: Unique execution plan identifier (UUID)
        rule_ids: Sorted list of rule_ids to execute (canonical order)
        created_at: ISO 8601 timestamp of plan creation
        batch_id: Identifier for the batch being audited (optional)
        metadata: Additional execution metadata (dict)
    """

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    rule_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    batch_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate plan on creation."""
        if not self.rule_ids:
            # Empty plans are valid (just log and skip)
            pass
        elif len(self.rule_ids) != len(set(self.rule_ids)):
            raise ValueError("Duplicate rule_ids in execution plan")

    @property
    def rule_count(self) -> int:
        """Total number of rules in plan.

        Returns:
            int: Number of rules
        """
        return len(self.rule_ids)

    @property
    def is_empty(self) -> bool:
        """Check if plan has no rules.

        Returns:
            bool: True if no rules, False otherwise
        """
        return len(self.rule_ids) == 0

    def as_dict(self) -> dict[str, Any]:
        """Serialize plan to dictionary.

        Returns:
            dict[str, Any]: Plan as dictionary with ISO timestamp
        """
        return {
            "plan_id": self.plan_id,
            "rule_ids": self.rule_ids,
            "created_at": self.created_at.isoformat(),
            "batch_id": self.batch_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ExecutionMetrics:
    """Immutable execution metrics for a rule or batch.

    Attributes:
        execution_time_ms: Total execution time in milliseconds
        findings_count: Number of findings emitted
        status: Execution status (success, failed, skipped)
        error_message: Error message if status is failed
    """

    execution_time_ms: float = 0.0
    findings_count: int = 0
    status: str = "success"  # success, failed, skipped
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate metrics."""
        valid_statuses = {"success", "failed", "skipped"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}")

        if self.status == "failed" and self.error_message is None:
            raise ValueError("error_message required when status is failed")


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry for rule execution.

    Attributes:
        entry_id: Unique entry identifier
        plan_id: Reference to execution plan
        rule_id: Rule being executed
        event_type: Type of event (plan_created, rule_started, rule_completed, etc.)
        timestamp: ISO 8601 timestamp
        metrics: Execution metrics (if applicable)
        details: Additional event details
    """

    entry_id: str = field(default_factory=lambda: str(uuid4()))
    plan_id: str = ""
    rule_id: str = ""
    event_type: str = ""  # plan_created, rule_started, rule_completed, error
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: ExecutionMetrics | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entry."""
        valid_events = {"plan_created", "rule_started", "rule_completed", "error", "batch_completed"}
        if self.event_type not in valid_events:
            raise ValueError(f"Invalid event_type: {self.event_type}")

    def as_dict(self) -> dict[str, Any]:
        """Serialize entry to dictionary.

        Returns:
            dict[str, Any]: Audit entry as dictionary
        """
        return {
            "entry_id": self.entry_id,
            "plan_id": self.plan_id,
            "rule_id": self.rule_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "metrics": {
                "execution_time_ms": self.metrics.execution_time_ms,
                "findings_count": self.metrics.findings_count,
                "status": self.metrics.status,
                "error_message": self.metrics.error_message,
            } if self.metrics else None,
            "details": self.details,
        }
