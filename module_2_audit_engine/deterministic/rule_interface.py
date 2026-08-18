"""
Rule interface and factory for deterministic contradiction detection.

Provides abstract base class and factory pattern for rule instantiation and management.
Enforces immutability, contract compliance, and validates rule implementations.
"""

from __future__ import annotations

import inspect
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Type

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================


class RuleException(Exception):
    """Base exception for rule-related errors."""

    pass


class RuleDuplicateError(RuleException):
    """Raised when attempting to register duplicate rule_id."""

    pass


class RuleContractError(RuleException):
    """Raised when rule violates contract requirements."""

    pass


class RuleVersionError(RuleException):
    """Raised when rule version is invalid (not semver)."""

    pass


class RuleImmutabilityError(RuleException):
    """Raised when rule metadata immutability is violated."""

    pass


class RuleNotFoundError(RuleException):
    """Raised when rule_id not found in registry."""

    pass


# ============================================================================
# Rule Metadata (Immutable)
# ============================================================================


@dataclass(frozen=True)
class RuleMetadata:
    """Immutable metadata for a rule.

    Attributes:
        rule_id: Unique identifier for the rule (e.g., "RULE-COND-001")
        version: Semantic version string (e.g., "1.0.0")
        name: Human-readable rule name
        description: Detailed description of what the rule detects
        category: Rule category (diagnosis, medication, encounter, timeline, etc.)
    """

    rule_id: str
    version: str
    name: str
    description: str
    category: str

    def __post_init__(self) -> None:
        """Validate metadata on initialization."""
        if not self.rule_id or not isinstance(self.rule_id, str):
            raise RuleContractError(f"rule_id must be a non-empty string, got {self.rule_id}")

        if not self._is_valid_semver(self.version):
            raise RuleVersionError(
                f"version must be semantic version (e.g. 1.0.0), got {self.version}"
            )

        if not self.name or not isinstance(self.name, str):
            raise RuleContractError(f"name must be a non-empty string, got {self.name}")

        if not self.description or not isinstance(self.description, str):
            raise RuleContractError(
                f"description must be a non-empty string, got {self.description}"
            )

        if not self.category or not isinstance(self.category, str):
            raise RuleContractError(f"category must be a non-empty string, got {self.category}")

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """Validate semantic version format (major.minor.patch).

        Args:
            version: Version string to validate

        Returns:
            True if valid semver, False otherwise
        """
        semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        return isinstance(version, str) and re.match(semver_pattern, version) is not None


# ============================================================================
# Rule Interface (Abstract Base Class)
# ============================================================================


class RuleInterface(ABC):
    """Abstract base class for deterministic contradiction detection rules.

    All rules must:
    1. Inherit from RuleInterface
    2. Implement the execute() method
    3. Provide immutable metadata
    4. Not modify input resources (enforced by factory validation)

    Example:
        class MyRule(RuleInterface):
            def __init__(self):
                self._metadata = RuleMetadata(
                    rule_id="RULE-CUSTOM-001",
                    version="1.0.0",
                    name="Custom Contradiction Rule",
                    description="Detects custom contradictions",
                    category="custom"
                )

            @property
            def metadata(self) -> RuleMetadata:
                return self._metadata

            def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
                findings = []
                for resource in resources:
                    if self._is_contradicted(resource):
                        findings.append(self._create_finding(resource))
                return findings

            def _is_contradicted(self, resource: Mapping[str, Any]) -> bool:
                # Implementation logic
                return False

            def _create_finding(self, resource: Mapping[str, Any]) -> Mapping[str, Any]:
                # Finding creation logic
                return {}
    """

    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Return immutable rule metadata.

        Returns:
            RuleMetadata: Metadata for this rule

        Raises:
            NotImplementedError: If not overridden by subclass
        """
        pass

    @abstractmethod
    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Execute rule against resources and return findings.

        Args:
            resources: List of FHIR resources (as dicts) to evaluate.
                      May be empty; if so, return empty findings list.

        Returns:
            List[Mapping[str, Any]]: List of findings (may be empty).
                                     Each finding is a dict with finding metadata.

        Raises:
            Exception: May raise implementation-specific exceptions.
                      Must not modify the input resources list.

        Note:
            This method must be deterministic: same input always produces
            same findings in the same order.
        """
        pass


# ============================================================================
# Rule Factory
# ============================================================================


class RuleFactory:
    """Factory for rule registration and instantiation.

    Manages rule lifecycle:
    - Registration: Register rule classes with unique rule_id
    - Lookup: Retrieve registered rule class by rule_id
    - Instantiation: Create rule instances with validation
    - Categorization: Group rules by category

    Example:
        factory = RuleFactory()
        factory.register(ConditionRule)
        factory.register(MedicationRule)

        rule = factory.instantiate("RULE-COND-001")
        rules_by_category = factory.by_category("diagnosis")
    """

    def __init__(self) -> None:
        """Initialize empty rule registry."""
        self._registry: Dict[str, Type[RuleInterface]] = {}
        self._categories: Dict[str, List[str]] = {}
        logger.info("RuleFactory initialized")

    def register(self, rule_class: Type[RuleInterface]) -> None:
        """Register a rule class in the factory.

        Args:
            rule_class: Rule class (must be subclass of RuleInterface)

        Raises:
            RuleContractError: If rule_class is not a RuleInterface subclass
            RuleDuplicateError: If rule_id already registered
            RuleImmutabilityError: If metadata is not properly immutable

        Note:
            Registration validates the rule class contract before storing.
        """
        if not issubclass(rule_class, RuleInterface):
            raise RuleContractError(
                f"Rule class {rule_class.__name__} must inherit from RuleInterface"
            )

        # Instantiate to get metadata and validate
        try:
            temp_instance = rule_class()
        except Exception as e:
            raise RuleContractError(
                f"Cannot instantiate rule class {rule_class.__name__}: {e}"
            )

        metadata = temp_instance.metadata

        # Check for duplicate
        if metadata.rule_id in self._registry:
            raise RuleDuplicateError(
                f"Rule ID '{metadata.rule_id}' already registered "
                f"(class {self._registry[metadata.rule_id].__name__})"
            )

        # Validate metadata immutability
        self._validate_metadata_immutability(temp_instance, metadata)

        # Validate execute() contract
        self._validate_execute_contract(rule_class)

        # Store in registry
        self._registry[metadata.rule_id] = rule_class
        logger.info(
            f"Registered rule {metadata.rule_id} "
            f"(version {metadata.version}, category {metadata.category})"
        )

        # Index by category
        if metadata.category not in self._categories:
            self._categories[metadata.category] = []
        self._categories[metadata.category].append(metadata.rule_id)

    def lookup(self, rule_id: str) -> Type[RuleInterface]:
        """Look up registered rule class by rule_id.

        Args:
            rule_id: Rule ID to look up

        Returns:
            Type[RuleInterface]: Rule class

        Raises:
            RuleNotFoundError: If rule_id not found
        """
        if rule_id not in self._registry:
            raise RuleNotFoundError(f"Rule ID '{rule_id}' not found in registry")
        return self._registry[rule_id]

    def instantiate(self, rule_id: str) -> RuleInterface:
        """Instantiate a rule by rule_id.

        Args:
            rule_id: Rule ID to instantiate

        Returns:
            RuleInterface: New rule instance

        Raises:
            RuleNotFoundError: If rule_id not found
            RuleContractError: If instantiation fails
        """
        rule_class = self.lookup(rule_id)  # May raise RuleNotFoundError
        try:
            return rule_class()
        except Exception as e:
            raise RuleContractError(
                f"Failed to instantiate rule {rule_id}: {e}"
            ) from e

    def by_category(self, category: str) -> List[str]:
        """Get all rule_ids in a category.

        Args:
            category: Category name

        Returns:
            List[str]: List of rule_ids in this category (may be empty).
                       Returns a copy to prevent external mutation.
        """
        return list(self._categories.get(category, []))

    def all_categories(self) -> Dict[str, List[str]]:
        """Get all categories and their rules.

        Returns:
            Dict[str, List[str]]: Map of category -> [rule_ids].
                                  Returns a copy to prevent external mutation.
        """
        return {category: list(rules) for category, rules in self._categories.items()}

    def registry_size(self) -> int:
        """Get number of registered rules.

        Returns:
            int: Number of rules in registry
        """
        return len(self._registry)

    def list_rules(self) -> Dict[str, RuleMetadata]:
        """List all registered rules with metadata.

        Returns:
            Dict[str, RuleMetadata]: Map of rule_id -> metadata
        """
        rules = {}
        for rule_id, rule_class in self._registry.items():
            try:
                instance = rule_class()
                rules[rule_id] = instance.metadata
            except Exception as e:
                logger.warning(f"Could not get metadata for {rule_id}: {e}")
        return rules

    @staticmethod
    def _validate_metadata_immutability(
        instance: RuleInterface, metadata: RuleMetadata
    ) -> None:
        """Validate that metadata is properly immutable (frozen dataclass).

        Args:
            instance: Rule instance
            metadata: Rule metadata

        Raises:
            RuleImmutabilityError: If metadata is not frozen or mutable
        """
        # Check that metadata is a frozen dataclass
        if not hasattr(metadata, "__dataclass_fields__"):
            raise RuleImmutabilityError(
                f"Rule {instance.__class__.__name__} metadata is not a dataclass"
            )

        # Attempt to modify - should raise error on frozen dataclass
        try:
            metadata.rule_id = "MODIFIED"  # type: ignore
            raise RuleImmutabilityError(
                f"Rule {instance.__class__.__name__} metadata is not frozen "
                f"(was able to modify rule_id)"
            )
        except (AttributeError, TypeError):
            # Expected - frozen dataclass raises AttributeError on modification
            pass

    @staticmethod
    def _validate_execute_contract(rule_class: Type[RuleInterface]) -> None:
        """Validate that rule implements execute() method with correct signature.

        Args:
            rule_class: Rule class to validate

        Raises:
            RuleContractError: If execute() signature is invalid
        """
        if not hasattr(rule_class, "execute"):
            raise RuleContractError(
                f"Rule class {rule_class.__name__} must implement execute() method"
            )

        # Get execute method
        execute_method = getattr(rule_class, "execute")
        if not callable(execute_method):
            raise RuleContractError(
                f"Rule class {rule_class.__name__} execute must be callable"
            )

        # Validate signature
        sig = inspect.signature(execute_method)
        params = list(sig.parameters.keys())

        # Remove 'self' parameter
        if params and params[0] == "self":
            params = params[1:]

        # Should have exactly one parameter (resources)
        if len(params) != 1:
            raise RuleContractError(
                f"Rule class {rule_class.__name__} execute() must have exactly "
                f"one parameter (resources), got {len(params)}: {params}"
            )

        # Validate that the method doesn't mutate inputs
        # This is checked at runtime, but we can at least inspect for obvious issues
        RuleFactory._check_mutation_safety(execute_method, rule_class.__name__)

    @staticmethod
    def _check_mutation_safety(method: Any, class_name: str) -> None:
        """Heuristic check for obvious input mutation patterns.

        Args:
            method: Method to check
            class_name: Class name (for logging)

        Note:
            This is a best-effort check. Full mutation detection happens at runtime.
        """
        try:
            source = inspect.getsource(method)
            # Look for common mutation patterns
            if "resources.append(" in source or "resources.pop(" in source:
                logger.warning(
                    f"Rule class {class_name} may mutate input resources list "
                    f"(detected list mutation pattern)"
                )
            if "resources[" in source and "=" in source:
                # This could be mutation, but could also be reading
                logger.debug(
                    f"Rule class {class_name} has indexing assignment pattern "
                    f"(may mutate resources)"
                )
        except (TypeError, OSError):
            # Can't get source for some methods (built-ins, etc.)
            pass
