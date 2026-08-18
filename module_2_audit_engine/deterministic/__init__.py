"""Deterministic rule engine components for audit engine.

Provides rule interfaces, factories, loaders, orchestration, and safety validation.
"""

from module_2_audit_engine.deterministic.audit_log import (
    AppendOnlyAuditLog,
    AuditLogEntry,
    AuditLogException,
    AuditLogWriteError,
)
from module_2_audit_engine.deterministic.orchestrator import (
    AuditLogger,
    PlanBuilder,
    ResultAggregator,
    RuleOrchestrator,
    OrchestratorException,
    PlanBuilderError,
    RuleExecutionError,
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
    RuleDuplicateInPackError,
    RulePackVersionError,
)
from module_2_audit_engine.deterministic.safety_validator import (
    SafetyBoundaryError,
    SafetyKeywordError,
    SafetyValidator,
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
    # Rule orchestrator (task_003)
    "RuleOrchestrator",
    "AuditLogger",
    "PlanBuilder",
    "ResultAggregator",
    "OrchestratorException",
    "PlanBuilderError",
    "RuleExecutionError",
    # Rule interface and factory
    "RuleInterface",
    "RuleMetadata",
    "RuleFactory",
    # Rule interface exceptions
    "RuleContractError",
    "RuleDuplicateError",
    "RuleImmutabilityError",
    "RuleNotFoundError",
    "RuleVersionError",
    # Rule loader
    "RulePackLoader",
    "ArchiveManager",
    # Rule loader exceptions
    "RulePackException",
    "RulePackParseError",
    "RulePackValidationError",
    "RuleDuplicateInPackError",
    "RulePackVersionError",
    "RulePackArchiveError",
]
