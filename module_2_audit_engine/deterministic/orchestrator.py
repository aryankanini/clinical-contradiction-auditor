"""Rule execution orchestrator with deterministic execution and audit logging.

Provides:
- Plan builder: load rule pack → extract rules → sort by rule_id → create plan
- Orchestrator: iterate plan in canonical order, execute each rule, collect findings
- Audit logger: log plan creation, rule execution, findings emission
- Result aggregator: combine findings with rule lineage
- Performance metrics: per-rule timing and batch statistics
"""

from __future__ import annotations

import logging
import time
from typing import Any, List, Mapping

from module_2_audit_engine.deterministic.rule_interface import RuleFactory, RuleInterface
from module_2_audit_engine.models.execution_plan import (
    AuditEntry,
    ExecutionMetrics,
    ExecutionPlan,
)
from module_2_audit_engine.models.rule_pack import RulePack

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================


class OrchestratorException(Exception):
    """Base exception for orchestrator errors."""

    pass


class PlanBuilderError(OrchestratorException):
    """Raised when execution plan creation fails."""

    pass


class RuleExecutionError(OrchestratorException):
    """Raised when rule execution fails."""

    pass


# ============================================================================
# Audit Logger
# ============================================================================


class AuditLogger:
    """Logs execution events for audit trail.

    Records plan creation, rule execution start/end, findings emission,
    and error events.
    """

    def __init__(self) -> None:
        """Initialize audit logger."""
        self.entries: List[AuditEntry] = []
        logger.info("AuditLogger initialized")

    def log_plan_created(self, plan: ExecutionPlan) -> None:
        """Log plan creation event.

        Args:
            plan: ExecutionPlan that was created
        """
        entry = AuditEntry(
            plan_id=plan.plan_id,
            event_type="plan_created",
            details={
                "rule_count": plan.rule_count,
                "rule_ids": plan.rule_ids,
            },
        )
        self.entries.append(entry)
        logger.info(
            f"Plan created: {plan.plan_id} with {plan.rule_count} rules"
        )

    def log_rule_started(self, plan_id: str, rule_id: str) -> None:
        """Log rule execution start.

        Args:
            plan_id: Execution plan ID
            rule_id: Rule ID being executed
        """
        entry = AuditEntry(
            plan_id=plan_id,
            rule_id=rule_id,
            event_type="rule_started",
        )
        self.entries.append(entry)
        logger.debug(f"Rule {rule_id} started (plan {plan_id})")

    def log_rule_completed(
        self,
        plan_id: str,
        rule_id: str,
        execution_time_ms: float,
        findings_count: int,
    ) -> None:
        """Log rule execution completion.

        Args:
            plan_id: Execution plan ID
            rule_id: Rule ID that completed
            execution_time_ms: Execution time in milliseconds
            findings_count: Number of findings emitted
        """
        # Warn if slow
        if execution_time_ms > 500:
            logger.warning(
                f"Rule {rule_id} slow execution: {execution_time_ms:.2f}ms"
            )

        metrics = ExecutionMetrics(
            execution_time_ms=execution_time_ms,
            findings_count=findings_count,
            status="success",
        )
        entry = AuditEntry(
            plan_id=plan_id,
            rule_id=rule_id,
            event_type="rule_completed",
            metrics=metrics,
        )
        self.entries.append(entry)
        logger.debug(
            f"Rule {rule_id} completed: {findings_count} findings, "
            f"{execution_time_ms:.2f}ms (plan {plan_id})"
        )

    def log_rule_error(
        self,
        plan_id: str,
        rule_id: str,
        error: Exception,
        execution_time_ms: float = 0.0,
    ) -> None:
        """Log rule execution error.

        Args:
            plan_id: Execution plan ID
            rule_id: Rule ID that errored
            error: Exception that occurred
            execution_time_ms: Execution time before error
        """
        error_msg = f"{type(error).__name__}: {str(error)}"
        metrics = ExecutionMetrics(
            execution_time_ms=execution_time_ms,
            findings_count=0,
            status="failed",
            error_message=error_msg,
        )
        entry = AuditEntry(
            plan_id=plan_id,
            rule_id=rule_id,
            event_type="error",
            metrics=metrics,
            details={"exception_type": type(error).__name__},
        )
        self.entries.append(entry)
        logger.error(
            f"Rule {rule_id} failed: {error_msg} (plan {plan_id})"
        )

    def log_batch_completed(
        self,
        plan_id: str,
        total_findings: int,
        total_time_ms: float,
    ) -> None:
        """Log batch completion.

        Args:
            plan_id: Execution plan ID
            total_findings: Total findings across all rules
            total_time_ms: Total batch execution time
        """
        metrics = ExecutionMetrics(
            execution_time_ms=total_time_ms,
            findings_count=total_findings,
            status="success",
        )
        entry = AuditEntry(
            plan_id=plan_id,
            event_type="batch_completed",
            metrics=metrics,
        )
        self.entries.append(entry)
        logger.info(
            f"Batch completed (plan {plan_id}): "
            f"{total_findings} total findings, {total_time_ms:.2f}ms"
        )

    def get_entries(self) -> List[AuditEntry]:
        """Get all audit entries.

        Returns:
            List[AuditEntry]: All logged entries
        """
        return list(self.entries)


# ============================================================================
# Plan Builder
# ============================================================================


class PlanBuilder:
    """Builds execution plans from rule packs.

    Extracts enabled rules from rule pack, sorts by rule_id (canonical order),
    and creates immutable execution plan.
    """

    @staticmethod
    def build(
        rule_pack: RulePack,
        batch_id: str | None = None,
    ) -> ExecutionPlan:
        """Build execution plan from rule pack.

        Args:
            rule_pack: RulePack to build plan from
            batch_id: Optional batch identifier

        Returns:
            ExecutionPlan: Immutable execution plan in canonical order

        Raises:
            PlanBuilderError: If plan creation fails

        Note:
            Rules are sorted by rule_id to ensure deterministic,
            reproducible execution order.
        """
        try:
            # Extract enabled rules
            enabled_rules = rule_pack.enabled_rules

            if not enabled_rules:
                logger.info(
                    f"Building empty plan (no enabled rules in pack "
                    f"{rule_pack.metadata.pack_id})"
                )
                return ExecutionPlan(
                    rule_ids=[],
                    batch_id=batch_id,
                    metadata={"pack_id": rule_pack.metadata.pack_id},
                )

            # Sort by rule_id (canonical order) → determinism
            rule_ids = sorted([rule.rule_id for rule in enabled_rules])

            logger.info(
                f"Built execution plan: {len(rule_ids)} rules from pack "
                f"{rule_pack.metadata.pack_id}, sorted by rule_id"
            )

            return ExecutionPlan(
                rule_ids=rule_ids,
                batch_id=batch_id,
                metadata={
                    "pack_id": rule_pack.metadata.pack_id,
                    "pack_version": rule_pack.metadata.version,
                },
            )
        except Exception as e:
            error_msg = f"Failed to build execution plan: {e}"
            logger.error(error_msg)
            raise PlanBuilderError(error_msg) from e


# ============================================================================
# Result Aggregator
# ============================================================================


class ResultAggregator:
    """Aggregates findings from multiple rules with lineage.

    Combines findings from all rule executions while preserving
    rule_id lineage for traceability.
    """

    @staticmethod
    def aggregate(
        findings_by_rule: dict[str, List[Mapping[str, Any]]],
    ) -> List[Mapping[str, Any]]:
        """Aggregate findings from all rules.

        Args:
            findings_by_rule: Map of rule_id -> findings list

        Returns:
            List[Mapping[str, Any]]: Aggregated findings with rule_id added

        Note:
            Each finding is enhanced with rule_id for traceability.
        """
        aggregated: List[Mapping[str, Any]] = []

        for rule_id, findings in findings_by_rule.items():
            for finding in findings:
                # Add rule_id lineage
                enriched_finding: dict[str, Any] = dict(finding)
                enriched_finding["rule_id"] = rule_id
                aggregated.append(enriched_finding)

        logger.debug(
            f"Aggregated {len(aggregated)} findings from "
            f"{len(findings_by_rule)} rules"
        )
        return aggregated


# ============================================================================
# Rule Orchestrator
# ============================================================================


class RuleOrchestrator:
    """Orchestrates deterministic rule execution.

    Executes rules in canonical order (sorted by rule_id) using
    fresh instances from factory, collects findings, and logs audit trail.

    Example:
        factory = RuleFactory()
        # ... register rules with factory ...

        pack = loader.load("rules.yaml")
        orchestrator = RuleOrchestrator(factory=factory)

        findings = orchestrator.execute(
            rule_pack=pack,
            resources=batch_resources,
        )
    """

    def __init__(self, factory: RuleFactory) -> None:
        """Initialize orchestrator.

        Args:
            factory: RuleFactory for rule instantiation
        """
        self.factory = factory
        self.audit_logger = AuditLogger()
        logger.info("RuleOrchestrator initialized")

    def execute(
        self,
        rule_pack: RulePack,
        resources: List[Mapping[str, Any]],
        batch_id: str | None = None,
    ) -> List[Mapping[str, Any]]:
        """Execute rule pack against resources deterministically.

        Args:
            rule_pack: Rule pack to execute
            resources: Resources to audit (FHIR resources as dicts)
            batch_id: Optional batch identifier for logging

        Returns:
            List[Mapping[str, Any]]: Aggregated findings with rule_id lineage

        Note:
            Execution is deterministic: same input → same findings in same order.
            Rules execute in sorted order (rule_id), not load order.
        """
        batch_start = time.time()

        # Build execution plan (logged before execution)
        plan = PlanBuilder.build(rule_pack, batch_id=batch_id)
        self.audit_logger.log_plan_created(plan)

        if plan.is_empty:
            logger.info(
                f"Batch {batch_id or 'unknown'}: empty plan, skipping execution"
            )
            return []

        # Execute rules in canonical order
        findings_by_rule: dict[str, List[Mapping[str, Any]]] = {}

        for rule_id in plan.rule_ids:
            rule_start = time.time()
            self.audit_logger.log_rule_started(plan.plan_id, rule_id)

            try:
                # Instantiate fresh rule from factory
                rule = self.factory.instantiate(rule_id)

                # Execute rule
                findings = rule.execute(resources)
                execution_time_ms = (time.time() - rule_start) * 1000

                # Log completion
                findings_by_rule[rule_id] = findings
                self.audit_logger.log_rule_completed(
                    plan.plan_id,
                    rule_id,
                    execution_time_ms,
                    len(findings),
                )

            except Exception as e:
                execution_time_ms = (time.time() - rule_start) * 1000
                self.audit_logger.log_rule_error(
                    plan.plan_id,
                    rule_id,
                    e,
                    execution_time_ms,
                )
                # Continue with next rule (don't break batch)
                findings_by_rule[rule_id] = [
                    {
                        "status": "FAILED",
                        "reason": str(e),
                        "type": type(e).__name__,
                    }
                ]

        # Aggregate findings
        aggregated = ResultAggregator.aggregate(findings_by_rule)

        # Log batch completion
        total_time_ms = (time.time() - batch_start) * 1000
        self.audit_logger.log_batch_completed(
            plan.plan_id,
            len(aggregated),
            total_time_ms,
        )

        logger.info(
            f"Batch execution complete (plan {plan.plan_id}): "
            f"executed {plan.rule_count} rules, "
            f"emitted {len(aggregated)} findings in {total_time_ms:.2f}ms"
        )

        return aggregated

    def get_audit_trail(self) -> List[AuditEntry]:
        """Get complete audit trail.

        Returns:
            List[AuditEntry]: All audit log entries
        """
        return self.audit_logger.get_entries()

    def get_metrics_for_plan(self, plan_id: str) -> dict[str, Any]:
        """Get aggregated metrics for a plan.

        Args:
            plan_id: Execution plan ID

        Returns:
            dict[str, Any]: Metrics including total time, findings, per-rule stats
        """
        entries = self.audit_logger.get_entries()
        plan_entries = [e for e in entries if e.plan_id == plan_id]

        if not plan_entries:
            return {}

        metrics: dict[str, Any] = {
            "plan_id": plan_id,
            "total_rules": 0,
            "successful_rules": 0,
            "failed_rules": 0,
            "total_findings": 0,
            "total_time_ms": 0.0,
            "per_rule_metrics": {},
        }

        for entry in plan_entries:
            if entry.event_type == "rule_completed" and entry.metrics:
                metrics["successful_rules"] += 1
                metrics["total_rules"] += 1
                metrics["total_findings"] += entry.metrics.findings_count
                metrics["per_rule_metrics"][entry.rule_id] = {
                    "execution_time_ms": entry.metrics.execution_time_ms,
                    "findings_count": entry.metrics.findings_count,
                }
            elif entry.event_type == "error" and entry.metrics:
                metrics["failed_rules"] += 1
                metrics["total_rules"] += 1
                metrics["per_rule_metrics"][entry.rule_id] = {
                    "execution_time_ms": entry.metrics.execution_time_ms,
                    "status": "failed",
                    "error": entry.metrics.error_message,
                }
            elif entry.event_type == "batch_completed" and entry.metrics:
                metrics["total_time_ms"] = entry.metrics.execution_time_ms

        return metrics
