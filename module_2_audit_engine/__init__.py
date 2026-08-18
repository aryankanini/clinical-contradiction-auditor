"""Audit engine package.

Provides deterministic contradiction detection rules for clinical data integrity auditing.

Core Components:
- RuleInterface: Abstract base class for all contradiction detection rules
- RuleFactory: Factory for rule registration and instantiation
- RuleMetadata: Immutable rule metadata (rule_id, version, category, etc.)
- RulePackLoader: Loader for YAML-based rule pack definitions
- RulePack: Pydantic model for rule pack schema
- RuleOrchestrator: Deterministic rule execution orchestrator
- ExecutionPlan: Immutable execution plan with canonical rule ordering
- SafetyValidator: Enforces safety boundaries (prevents unsafe keywords)
- AppendOnlyAuditLog: Append-only audit trail for reproducibility
- Finding: Immutable finding model
"""

from module_2_audit_engine.deterministic.audit_log import (
    AppendOnlyAuditLog,
    AuditLogEntry,
    AuditLogException,
    AuditLogWriteError,
)
from module_2_audit_engine.deterministic.orchestrator import (
    AuditLogger,
    OrchestratorException,
    PlanBuilder,
    PlanBuilderError,
    ResultAggregator,
    RuleExecutionError,
    RuleOrchestrator,
)
from module_2_audit_engine.deterministic.rule_interface import (
    RuleContractError,
    RuleDuplicateError,
    RuleFactory,
    RuleInterface,
    RuleImmutabilityError,
    RuleMetadata,
    RuleNotFoundError,
    RuleVersionError,
)
from module_2_audit_engine.deterministic.rule_loader import (
    ArchiveManager,
    RulePackArchiveError,
    RulePackException,
    RulePackLoader,
    RulePackParseError,
    RulePackValidationError,
)
from module_2_audit_engine.deterministic.safety_validator import (
    SafetyBoundaryError,
    SafetyKeywordError,
    SafetyValidator,
)
from module_2_audit_engine.models.execution_plan import (
    AuditEntry,
    ExecutionMetrics,
    ExecutionPlan,
)
from module_2_audit_engine.models.finding import Finding
from module_2_audit_engine.models.rule_pack import (
    RuleDefinition,
    RulePack,
    RulePackMetadata,
)

__all__ = [
    # Safety validator (task_004)
    "SafetyValidator",
    "SafetyBoundaryError",
    "SafetyKeywordError",
    # Audit log (task_004)
    "AppendOnlyAuditLog",
    "AuditLogEntry",
    "AuditLogException",
    "AuditLogWriteError",
    # Finding model (task_004)
    "Finding",
    # Rule orchestrator (task_003)
    "RuleOrchestrator",
    "PlanBuilder",
    "AuditLogger",
    "ResultAggregator",
    "OrchestratorException",
    "PlanBuilderError",
    "RuleExecutionError",
    # Execution plan models
    "ExecutionPlan",
    "ExecutionMetrics",
    "AuditEntry",
    # Rule interface (task_001)
    "RuleInterface",
    "RuleMetadata",
    "RuleFactory",
    "RuleContractError",
    "RuleDuplicateError",
    "RuleImmutabilityError",
    "RuleNotFoundError",
    "RuleVersionError",
    # Rule loader (task_002)
    "RulePackLoader",
    "ArchiveManager",
    "RulePackException",
    "RulePackParseError",
    "RulePackValidationError",
    "RulePackArchiveError",
    # Rule pack models
    "RulePack",
    "RulePackMetadata",
    "RuleDefinition",
]