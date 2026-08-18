"""Append-only audit log infrastructure.

Provides immutable, append-only audit trail recording for compliance and
reproducibility. Supports batch-level audit entries with metrics tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditLogException(Exception):
    """Base exception for audit log operations."""

    pass


class AuditLogWriteError(AuditLogException):
    """Raised when audit log write fails."""

    pass


@dataclass(frozen=True)
class AuditLogEntry:
    """Immutable audit log entry.

    Represents a single entry in the append-only audit trail.
    Frozen dataclass ensures immutability and reproducibility.

    Attributes:
        entry_id: Unique entry ID (UUID)
        batch_run_id: Batch execution ID
        rule_pack_version: Version of rule pack used
        timestamp_utc: Entry creation timestamp (UTC)
        findings_count: Number of findings emitted
        status: Entry status (success, failed, partial)
        error_message: Error message if status is failed
        metadata: Additional entry metadata
    """

    entry_id: str = field(default_factory=lambda: str(uuid4()))
    batch_run_id: str = ""
    rule_pack_version: str = ""
    timestamp_utc: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    findings_count: int = 0
    status: str = "success"  # success, failed, partial
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entry after initialization."""
        if self.status not in ("success", "failed", "partial"):
            raise ValueError(
                f"Invalid status '{self.status}': "
                "must be success, failed, or partial"
            )

    def as_dict(self) -> dict[str, Any]:
        """Serialize entry to dictionary.

        Returns:
            dict[str, Any]: Entry as dictionary with ISO timestamp
        """
        return {
            "entry_id": self.entry_id,
            "batch_run_id": self.batch_run_id,
            "rule_pack_version": self.rule_pack_version,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "findings_count": self.findings_count,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }


class AppendOnlyAuditLog:
    """Append-only audit log.

    Records immutable audit trail entries. Supports append-only writes
    (no UPDATE or DELETE) for compliance and reproducibility.

    Guarantees:
        - Each entry immutable after creation
        - Entries sorted by timestamp
        - No modifications allowed (append-only semantics)
        - Suitable for compliance/reproducibility requirements
    """

    def __init__(self) -> None:
        """Initialize audit log."""
        self.entries: list[AuditLogEntry] = []
        logger.debug("AppendOnlyAuditLog initialized")

    def append_entry(
        self,
        batch_run_id: str,
        findings_count: int,
        rule_pack_version: str = "",
        status: str = "success",
        error_message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Append entry to audit log.

        Creates immutable entry and appends to log (INSERT semantics only).

        Args:
            batch_run_id: Batch execution ID
            findings_count: Number of findings emitted
            rule_pack_version: Version of rule pack (optional)
            status: Entry status (success, failed, partial)
            error_message: Error message if applicable
            metadata: Additional metadata

        Returns:
            AuditLogEntry: Created and appended entry

        Raises:
            AuditLogWriteError: If append fails
        """
        try:
            entry = AuditLogEntry(
                batch_run_id=batch_run_id,
                rule_pack_version=rule_pack_version,
                findings_count=findings_count,
                status=status,
                error_message=error_message,
                metadata=metadata or {},
            )

            self.entries.append(entry)
            logger.info(
                f"Audit log entry appended: batch_id={batch_run_id}, "
                f"findings={findings_count}, status={status}"
            )

            return entry
        except Exception as e:
            raise AuditLogWriteError(f"Failed to append audit log entry: {e}")

    def get_all_entries(self) -> list[AuditLogEntry]:
        """Get all audit log entries.

        Returns:
            list[AuditLogEntry]: All entries in chronological order
        """
        return list(self.entries)

    def get_entries_for_batch(self, batch_run_id: str) -> list[AuditLogEntry]:
        """Get entries for specific batch.

        Args:
            batch_run_id: Batch ID to filter by

        Returns:
            list[AuditLogEntry]: Entries for batch
        """
        return [e for e in self.entries if e.batch_run_id == batch_run_id]

    def get_statistics(self) -> dict[str, Any]:
        """Get audit log statistics.

        Returns:
            dict[str, Any]: Statistics including entry count, status breakdown
        """
        total_entries = len(self.entries)
        successful = sum(1 for e in self.entries if e.status == "success")
        failed = sum(1 for e in self.entries if e.status == "failed")
        partial = sum(1 for e in self.entries if e.status == "partial")

        return {
            "total_entries": total_entries,
            "successful": successful,
            "failed": failed,
            "partial": partial,
            "total_findings": sum(e.findings_count for e in self.entries),
        }
