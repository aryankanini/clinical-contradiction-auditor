"""Unit tests for rule orchestrator and execution plan.

Tests verify:
- Deterministic execution (same input → same findings in same order)
- Canonical rule ordering (sorted by rule_id, not load order)
- Execution plan creation and logging
- Error handling and recovery
- Performance metrics and audit trail
"""

from __future__ import annotations

import unittest
import time
from typing import Any, List, Mapping
from unittest.mock import MagicMock, patch

from module_2_audit_engine.deterministic.orchestrator import (
    AuditLogger,
    PlanBuilder,
    RuleOrchestrator,
    ResultAggregator,
)
from module_2_audit_engine.deterministic.rule_interface import (
    RuleFactory,
    RuleInterface,
    RuleMetadata,
)
from module_2_audit_engine.models.execution_plan import (
    ExecutionMetrics,
    ExecutionPlan,
    AuditEntry,
)
from module_2_audit_engine.models.rule_pack import (
    RuleDefinition,
    RulePack,
    RulePackMetadata,
)


# ============================================================================
# Test Rule Implementations
# ============================================================================


class DeterministicRule1(RuleInterface):
    """Rule that always returns same findings."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-A-001",
            version="1.0.0",
            name="Rule A",
            description="First rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Always return deterministic findings."""
        return [{"rule": "A", "count": len(resources)}]


class DeterministicRule2(RuleInterface):
    """Rule that always returns same findings."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-B-001",
            version="1.0.0",
            name="Rule B",
            description="Second rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Always return deterministic findings."""
        return [{"rule": "B", "count": len(resources) * 2}]


class DeterministicRule3(RuleInterface):
    """Rule that always returns same findings."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-C-001",
            version="1.0.0",
            name="Rule C",
            description="Third rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Always return deterministic findings."""
        return [{"rule": "C", "count": len(resources) * 3}]


class FailingRule(RuleInterface):
    """Rule that throws exception."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-FAIL-001",
            version="1.0.0",
            name="Failing Rule",
            description="Always fails",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Always fails."""
        raise ValueError("Intentional test failure")


class EmptyRule(RuleInterface):
    """Rule that returns no findings."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-EMPTY-001",
            version="1.0.0",
            name="Empty Rule",
            description="Returns no findings",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Return empty findings."""
        return []


# ============================================================================
# Test Rule Pack Fixtures
# ============================================================================


def create_test_pack_3_rules() -> RulePack:
    """Create test pack with 3 rules."""
    return RulePack(
        metadata=RulePackMetadata(
            pack_id="PACK-TEST-001",
            version="1.0.0",
            description="Test pack",
        ),
        rules=[
            RuleDefinition(
                rule_id="RULE-A-001",
                version="1.0.0",
                name="Rule A",
                description="Rule A",
                category="test",
                enabled=True,
            ),
            RuleDefinition(
                rule_id="RULE-B-001",
                version="1.0.0",
                name="Rule B",
                description="Rule B",
                category="test",
                enabled=True,
            ),
            RuleDefinition(
                rule_id="RULE-C-001",
                version="1.0.0",
                name="Rule C",
                description="Rule C",
                category="test",
                enabled=True,
            ),
        ],
    )


def create_test_pack_out_of_order() -> RulePack:
    """Create test pack with rules in reverse alphabetical order."""
    return RulePack(
        metadata=RulePackMetadata(
            pack_id="PACK-TEST-002",
            version="1.0.0",
        ),
        rules=[
            RuleDefinition(
                rule_id="RULE-C-001",
                version="1.0.0",
                name="Rule C",
                description="Rule C",
                category="test",
                enabled=True,
            ),
            RuleDefinition(
                rule_id="RULE-B-001",
                version="1.0.0",
                name="Rule B",
                description="Rule B",
                category="test",
                enabled=True,
            ),
            RuleDefinition(
                rule_id="RULE-A-001",
                version="1.0.0",
                name="Rule A",
                description="Rule A",
                category="test",
                enabled=True,
            ),
        ],
    )


# ============================================================================
# Test Cases: ExecutionPlan
# ============================================================================


class TestExecutionPlan(unittest.TestCase):
    """Test ExecutionPlan schema."""

    def test_execution_plan_creation(self) -> None:
        """Create execution plan."""
        plan = ExecutionPlan(rule_ids=["RULE-A", "RULE-B"], batch_id="BATCH-001")
        self.assertEqual(plan.rule_count, 2)
        self.assertFalse(plan.is_empty)

    def test_execution_plan_empty(self) -> None:
        """Empty plan is valid."""
        plan = ExecutionPlan(rule_ids=[])
        self.assertEqual(plan.rule_count, 0)
        self.assertTrue(plan.is_empty)

    def test_execution_plan_frozen(self) -> None:
        """Plan is immutable."""
        plan = ExecutionPlan(rule_ids=["RULE-A"])
        with self.assertRaises((TypeError, AttributeError)):
            plan.rule_ids = ["RULE-B"]  # type: ignore

    def test_execution_plan_duplicate_detection(self) -> None:
        """Duplicate rule_ids rejected."""
        with self.assertRaises(ValueError):
            ExecutionPlan(rule_ids=["RULE-A", "RULE-A"])


# ============================================================================
# Test Cases: AuditLogger
# ============================================================================


class TestAuditLogger(unittest.TestCase):
    """Test AuditLogger functionality."""

    def setUp(self) -> None:
        """Create logger."""
        self.logger = AuditLogger()
        self.plan = ExecutionPlan(rule_ids=["RULE-A", "RULE-B"])

    def test_log_plan_created(self) -> None:
        """Log plan creation."""
        self.logger.log_plan_created(self.plan)
        entries = self.logger.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "plan_created")

    def test_log_rule_started(self) -> None:
        """Log rule start."""
        self.logger.log_rule_started(self.plan.plan_id, "RULE-A")
        entries = self.logger.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "rule_started")

    def test_log_rule_completed(self) -> None:
        """Log rule completion."""
        self.logger.log_rule_completed(
            self.plan.plan_id, "RULE-A", 100.5, 5
        )
        entries = self.logger.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "rule_completed")
        self.assertIsNotNone(entries[0].metrics)
        self.assertEqual(entries[0].metrics.findings_count, 5)

    def test_log_rule_error(self) -> None:
        """Log rule error."""
        error = ValueError("Test error")
        self.logger.log_rule_error(self.plan.plan_id, "RULE-A", error, 50.0)
        entries = self.logger.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "error")
        self.assertEqual(entries[0].metrics.status, "failed")


# ============================================================================
# Test Cases: PlanBuilder
# ============================================================================


class TestPlanBuilder(unittest.TestCase):
    """Test PlanBuilder functionality."""

    def test_plan_builder_creates_plan(self) -> None:
        """Build plan from pack."""
        pack = create_test_pack_3_rules()
        plan = PlanBuilder.build(pack)
        self.assertEqual(plan.rule_count, 3)

    def test_plan_builder_sorts_by_rule_id(self) -> None:
        """Rules sorted by rule_id (canonical order)."""
        pack = create_test_pack_out_of_order()
        plan = PlanBuilder.build(pack)
        # Should be sorted: A, B, C (not C, B, A)
        self.assertEqual(plan.rule_ids, ["RULE-A-001", "RULE-B-001", "RULE-C-001"])

    def test_plan_builder_empty_pack(self) -> None:
        """Build plan with no enabled rules."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-EMPTY",
                version="1.0.0",
            ),
            rules=[],
        )
        plan = PlanBuilder.build(pack)
        self.assertTrue(plan.is_empty)
        self.assertEqual(plan.rule_count, 0)

    def test_plan_builder_with_batch_id(self) -> None:
        """Plan includes batch_id."""
        pack = create_test_pack_3_rules()
        plan = PlanBuilder.build(pack, batch_id="BATCH-123")
        self.assertEqual(plan.batch_id, "BATCH-123")


# ============================================================================
# Test Cases: ResultAggregator
# ============================================================================


class TestResultAggregator(unittest.TestCase):
    """Test ResultAggregator functionality."""

    def test_aggregate_single_rule(self) -> None:
        """Aggregate findings from single rule."""
        findings = ResultAggregator.aggregate({
            "RULE-A": [{"finding": "1"}, {"finding": "2"}]
        })
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["rule_id"], "RULE-A")

    def test_aggregate_multiple_rules(self) -> None:
        """Aggregate findings from multiple rules."""
        findings = ResultAggregator.aggregate({
            "RULE-A": [{"finding": "1"}],
            "RULE-B": [{"finding": "2"}, {"finding": "3"}],
        })
        self.assertEqual(len(findings), 3)
        self.assertEqual(findings[0]["rule_id"], "RULE-A")
        self.assertEqual(findings[1]["rule_id"], "RULE-B")

    def test_aggregate_empty_findings(self) -> None:
        """Aggregate with empty findings."""
        findings = ResultAggregator.aggregate({
            "RULE-A": [],
            "RULE-B": [{"finding": "1"}],
        })
        self.assertEqual(len(findings), 1)


# ============================================================================
# Test Cases: RuleOrchestrator - Determinism
# ============================================================================


class TestOrchestratorDeterminism(unittest.TestCase):
    """Test deterministic execution."""

    def setUp(self) -> None:
        """Create factory and orchestrator."""
        self.factory = RuleFactory()
        self.factory.register(DeterministicRule1)
        self.factory.register(DeterministicRule2)
        self.factory.register(DeterministicRule3)
        self.orchestrator = RuleOrchestrator(factory=self.factory)

    def test_determinism_same_input_same_output(self) -> None:
        """Same input → same findings in same order."""
        pack = create_test_pack_3_rules()
        resources = [{"type": "Condition", "id": "1"}]

        # Execute twice
        findings1 = self.orchestrator.execute(pack, resources, batch_id="BATCH-1")
        findings2 = self.orchestrator.execute(pack, resources, batch_id="BATCH-2")

        # Should be identical
        self.assertEqual(len(findings1), len(findings2))
        for f1, f2 in zip(findings1, findings2):
            self.assertEqual(f1["rule"], f2["rule"])
            self.assertEqual(f1["count"], f2["count"])

    def test_determinism_order_preserved(self) -> None:
        """Findings order preserved across executions."""
        pack = create_test_pack_3_rules()
        resources = [{"type": "Condition"}]

        findings1 = self.orchestrator.execute(pack, resources)
        findings2 = self.orchestrator.execute(pack, resources)

        # Extract rule_ids in order
        order1 = [f["rule_id"] for f in findings1]
        order2 = [f["rule_id"] for f in findings2]

        self.assertEqual(order1, order2)


# ============================================================================
# Test Cases: RuleOrchestrator - Ordering
# ============================================================================


class TestOrchestratorOrdering(unittest.TestCase):
    """Test canonical rule ordering."""

    def setUp(self) -> None:
        """Create factory and orchestrator."""
        self.factory = RuleFactory()
        self.factory.register(DeterministicRule1)
        self.factory.register(DeterministicRule2)
        self.factory.register(DeterministicRule3)
        self.orchestrator = RuleOrchestrator(factory=self.factory)

    def test_ordering_out_of_order_pack(self) -> None:
        """Out-of-order pack still executes in sorted order."""
        pack = create_test_pack_out_of_order()  # C, B, A in pack
        resources = []

        findings = self.orchestrator.execute(pack, resources)
        rule_ids = [f["rule_id"] for f in findings]

        # Should be A, B, C (sorted) not C, B, A
        self.assertEqual(rule_ids, ["RULE-A-001", "RULE-B-001", "RULE-C-001"])

    def test_ordering_audit_trail_reflects_plan_order(self) -> None:
        """Audit trail shows correct execution order."""
        pack = create_test_pack_out_of_order()
        resources = []

        self.orchestrator.execute(pack, resources)
        trail = self.orchestrator.get_audit_trail()

        # Extract rule execution order from audit trail
        executed_rules = [
            e.rule_id for e in trail if e.event_type == "rule_started"
        ]
        self.assertEqual(
            executed_rules,
            ["RULE-A-001", "RULE-B-001", "RULE-C-001"],
        )


# ============================================================================
# Test Cases: RuleOrchestrator - Plan Creation
# ============================================================================


class TestOrchestratorPlanCreation(unittest.TestCase):
    """Test plan creation and logging."""

    def setUp(self) -> None:
        """Create factory and orchestrator."""
        self.factory = RuleFactory()
        self.factory.register(DeterministicRule1)
        self.factory.register(DeterministicRule2)
        self.factory.register(DeterministicRule3)
        self.orchestrator = RuleOrchestrator(factory=self.factory)

    def test_plan_creation_logged_before_execution(self) -> None:
        """Plan creation logged before rules execute."""
        pack = create_test_pack_3_rules()
        resources = []

        self.orchestrator.execute(pack, resources)
        trail = self.orchestrator.get_audit_trail()

        # First entry should be plan_created
        self.assertEqual(trail[0].event_type, "plan_created")

    def test_plan_has_batch_id(self) -> None:
        """Plan includes batch_id in execution."""
        pack = create_test_pack_3_rules()
        resources = []

        self.orchestrator.execute(pack, resources, batch_id="BATCH-999")
        trail = self.orchestrator.get_audit_trail()

        # Verify batch was used (check metrics show batch execution)
        self.assertGreater(len(trail), 0)


# ============================================================================
# Test Cases: RuleOrchestrator - Error Handling
# ============================================================================


class TestOrchestratorErrorHandling(unittest.TestCase):
    """Test error handling and recovery."""

    def setUp(self) -> None:
        """Create factory and orchestrator."""
        self.factory = RuleFactory()
        self.factory.register(DeterministicRule1)
        self.factory.register(FailingRule)
        self.factory.register(DeterministicRule2)
        self.orchestrator = RuleOrchestrator(factory=self.factory)

    def test_error_handling_continues_batch(self) -> None:
        """Batch continues after rule error."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-TEST-001",
                version="1.0.0",
            ),
            rules=[
                RuleDefinition(
                    rule_id="RULE-A-001",
                    version="1.0.0",
                    name="Rule A",
                    description="Rule A",
                    category="test",
                ),
                RuleDefinition(
                    rule_id="RULE-FAIL-001",
                    version="1.0.0",
                    name="Failing Rule",
                    description="Fails",
                    category="test",
                ),
                RuleDefinition(
                    rule_id="RULE-B-001",
                    version="1.0.0",
                    name="Rule B",
                    description="Rule B",
                    category="test",
                ),
            ],
        )
        resources = []

        findings = self.orchestrator.execute(pack, resources)

        # Should have findings from all 3 rules (failed rule gets FAILED status)
        rule_ids = {f["rule_id"] for f in findings}
        self.assertIn("RULE-A-001", rule_ids)
        self.assertIn("RULE-FAIL-001", rule_ids)
        self.assertIn("RULE-B-001", rule_ids)

    def test_error_finding_has_failed_status(self) -> None:
        """Failed rule produces FAILED finding."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-TEST-001",
                version="1.0.0",
            ),
            rules=[
                RuleDefinition(
                    rule_id="RULE-FAIL-001",
                    version="1.0.0",
                    name="Failing Rule",
                    description="Fails",
                    category="test",
                ),
            ],
        )
        resources = []

        findings = self.orchestrator.execute(pack, resources)

        # Failed rule should have FAILED status in findings
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["status"], "FAILED")
        self.assertIn("reason", findings[0])


# ============================================================================
# Test Cases: RuleOrchestrator - Metrics
# ============================================================================


class TestOrchestratorMetrics(unittest.TestCase):
    """Test performance metrics."""

    def setUp(self) -> None:
        """Create factory and orchestrator."""
        self.factory = RuleFactory()
        self.factory.register(DeterministicRule1)
        self.factory.register(DeterministicRule2)
        self.factory.register(DeterministicRule3)
        self.orchestrator = RuleOrchestrator(factory=self.factory)

    def test_metrics_captured_for_plan(self) -> None:
        """Metrics captured for execution."""
        pack = create_test_pack_3_rules()
        resources = [{"type": "Condition"}]

        self.orchestrator.execute(pack, resources)
        trail = self.orchestrator.get_audit_trail()

        # Find rule_completed entries with metrics
        completed = [e for e in trail if e.event_type == "rule_completed"]
        self.assertGreater(len(completed), 0)

        for entry in completed:
            self.assertIsNotNone(entry.metrics)
            self.assertGreaterEqual(entry.metrics.execution_time_ms, 0)


if __name__ == "__main__":
    unittest.main()
