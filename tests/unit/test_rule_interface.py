"""Unit tests for rule interface and factory.

Tests verify:
- RuleInterface contract enforcement
- RuleFactory registration and lookup
- Metadata immutability
- Validation error cases
- Edge cases (duplicate registration, missing methods, etc.)
"""

from __future__ import annotations

import unittest
from typing import Any, List, Mapping

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


# ============================================================================
# Test Rule Implementations
# ============================================================================


class SimpleTestRule(RuleInterface):
    """Simple test rule implementation."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-TEST-001",
            version="1.0.0",
            name="Simple Test Rule",
            description="Test rule for validation",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Execute test rule."""
        return []


class AnotherTestRule(RuleInterface):
    """Another test rule for factory testing."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-TEST-002",
            version="2.0.0",
            name="Another Test Rule",
            description="Another test rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Execute test rule."""
        return []


class DiagnosisTestRule(RuleInterface):
    """Test rule in diagnosis category."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-COND-999",
            version="1.0.0",
            name="Diagnosis Test Rule",
            description="Test diagnosis rule",
            category="diagnosis",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Execute test rule."""
        return []


class MedicationTestRule(RuleInterface):
    """Test rule in medication category."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-MED-999",
            version="1.1.0",
            name="Medication Test Rule",
            description="Test medication rule",
            category="medication",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        """Execute test rule."""
        return []


class MissingExecuteRule(RuleInterface):
    """Invalid rule missing execute method."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-BAD-001",
            version="1.0.0",
            name="Bad Rule",
            description="Invalid rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    # Missing execute() implementation!


class WrongSignatureRule(RuleInterface):
    """Rule with wrong execute signature."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="RULE-BAD-002",
            version="1.0.0",
            name="Wrong Signature Rule",
            description="Invalid rule",
            category="test",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(self, resources: List[Mapping[str, Any]], extra_param: str) -> List[Mapping[str, Any]]:
        """Execute with wrong signature."""
        return []


# ============================================================================
# Test Cases: RuleMetadata
# ============================================================================


class TestRuleMetadata(unittest.TestCase):
    """Test RuleMetadata validation and immutability."""

    def test_metadata_creation_valid(self) -> None:
        """Valid metadata creation."""
        metadata = RuleMetadata(
            rule_id="RULE-TEST-001",
            version="1.0.0",
            name="Test Rule",
            description="Test description",
            category="test",
        )
        self.assertEqual(metadata.rule_id, "RULE-TEST-001")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.name, "Test Rule")

    def test_metadata_frozen(self) -> None:
        """Metadata is frozen (immutable)."""
        metadata = RuleMetadata(
            rule_id="RULE-TEST-001",
            version="1.0.0",
            name="Test Rule",
            description="Test description",
            category="test",
        )
        # Attempting to modify should raise AttributeError (frozen dataclass)
        with self.assertRaises((AttributeError, TypeError)):
            metadata.rule_id = "MODIFIED"  # type: ignore

    def test_metadata_invalid_version(self) -> None:
        """Invalid semver version rejected."""
        with self.assertRaises(RuleVersionError):
            RuleMetadata(
                rule_id="RULE-TEST-001",
                version="not-a-version",
                name="Test Rule",
                description="Test description",
                category="test",
            )

    def test_metadata_empty_rule_id(self) -> None:
        """Empty rule_id rejected."""
        with self.assertRaises(RuleContractError):
            RuleMetadata(
                rule_id="",
                version="1.0.0",
                name="Test Rule",
                description="Test description",
                category="test",
            )

    def test_metadata_empty_name(self) -> None:
        """Empty name rejected."""
        with self.assertRaises(RuleContractError):
            RuleMetadata(
                rule_id="RULE-TEST-001",
                version="1.0.0",
                name="",
                description="Test description",
                category="test",
            )


# ============================================================================
# Test Cases: RuleFactory Registration
# ============================================================================


class TestRuleFactoryRegistration(unittest.TestCase):
    """Test RuleFactory registration functionality."""

    def setUp(self) -> None:
        """Create fresh factory for each test."""
        self.factory = RuleFactory()

    def test_factory_register_single_rule(self) -> None:
        """Register single rule successfully."""
        self.factory.register(SimpleTestRule)
        self.assertEqual(self.factory.registry_size(), 1)

    def test_factory_register_multiple_rules(self) -> None:
        """Register multiple rules."""
        self.factory.register(SimpleTestRule)
        self.factory.register(AnotherTestRule)
        self.factory.register(DiagnosisTestRule)
        self.assertEqual(self.factory.registry_size(), 3)

    def test_factory_register_duplicate_rule_id(self) -> None:
        """Duplicate rule_id registration raises error."""
        self.factory.register(SimpleTestRule)
        with self.assertRaises(RuleDuplicateError):
            self.factory.register(SimpleTestRule)

    def test_factory_register_non_rule_interface_class(self) -> None:
        """Non-RuleInterface class rejected."""

        class NotARule:
            pass

        with self.assertRaises(RuleContractError):
            self.factory.register(NotARule)  # type: ignore

    def test_factory_register_missing_execute(self) -> None:
        """Rule missing execute() method rejected."""
        with self.assertRaises(RuleContractError):
            self.factory.register(MissingExecuteRule)

    def test_factory_register_wrong_signature(self) -> None:
        """Rule with wrong execute() signature rejected."""
        with self.assertRaises(RuleContractError):
            self.factory.register(WrongSignatureRule)


# ============================================================================
# Test Cases: RuleFactory Lookup
# ============================================================================


class TestRuleFactoryLookup(unittest.TestCase):
    """Test RuleFactory lookup functionality."""

    def setUp(self) -> None:
        """Create and populate factory."""
        self.factory = RuleFactory()
        self.factory.register(SimpleTestRule)
        self.factory.register(AnotherTestRule)

    def test_factory_lookup_existing_rule(self) -> None:
        """Lookup existing rule returns correct class."""
        rule_class = self.factory.lookup("RULE-TEST-001")
        self.assertEqual(rule_class, SimpleTestRule)

    def test_factory_lookup_another_rule(self) -> None:
        """Lookup another rule returns correct class."""
        rule_class = self.factory.lookup("RULE-TEST-002")
        self.assertEqual(rule_class, AnotherTestRule)

    def test_factory_lookup_nonexistent_rule(self) -> None:
        """Lookup nonexistent rule raises RuleNotFoundError."""
        with self.assertRaises(RuleNotFoundError):
            self.factory.lookup("RULE-NONEXISTENT-001")

    def test_factory_instantiate_rule(self) -> None:
        """Instantiate rule by rule_id."""
        rule = self.factory.instantiate("RULE-TEST-001")
        self.assertIsInstance(rule, SimpleTestRule)
        self.assertEqual(rule.metadata.rule_id, "RULE-TEST-001")

    def test_factory_instantiate_nonexistent_rule(self) -> None:
        """Instantiate nonexistent rule raises RuleNotFoundError."""
        with self.assertRaises(RuleNotFoundError):
            self.factory.instantiate("RULE-NONEXISTENT-001")


# ============================================================================
# Test Cases: RuleFactory Categories
# ============================================================================


class TestRuleFactoryCategories(unittest.TestCase):
    """Test RuleFactory categorization."""

    def setUp(self) -> None:
        """Create and populate factory."""
        self.factory = RuleFactory()
        self.factory.register(SimpleTestRule)  # category: test
        self.factory.register(AnotherTestRule)  # category: test
        self.factory.register(DiagnosisTestRule)  # category: diagnosis
        self.factory.register(MedicationTestRule)  # category: medication

    def test_factory_by_category_test(self) -> None:
        """Get rules in test category."""
        test_rules = self.factory.by_category("test")
        self.assertEqual(len(test_rules), 2)
        self.assertIn("RULE-TEST-001", test_rules)
        self.assertIn("RULE-TEST-002", test_rules)

    def test_factory_by_category_diagnosis(self) -> None:
        """Get rules in diagnosis category."""
        diagnosis_rules = self.factory.by_category("diagnosis")
        self.assertEqual(len(diagnosis_rules), 1)
        self.assertIn("RULE-COND-999", diagnosis_rules)

    def test_factory_by_category_medication(self) -> None:
        """Get rules in medication category."""
        medication_rules = self.factory.by_category("medication")
        self.assertEqual(len(medication_rules), 1)
        self.assertIn("RULE-MED-999", medication_rules)

    def test_factory_by_category_empty(self) -> None:
        """Get rules in nonexistent category returns empty."""
        other_rules = self.factory.by_category("nonexistent")
        self.assertEqual(len(other_rules), 0)

    def test_factory_all_categories(self) -> None:
        """Get all categories."""
        categories = self.factory.all_categories()
        self.assertIn("test", categories)
        self.assertIn("diagnosis", categories)
        self.assertIn("medication", categories)
        self.assertEqual(len(categories["test"]), 2)


# ============================================================================
# Test Cases: RuleFactory Listing
# ============================================================================


class TestRuleFactoryListing(unittest.TestCase):
    """Test RuleFactory listing functionality."""

    def setUp(self) -> None:
        """Create and populate factory."""
        self.factory = RuleFactory()
        self.factory.register(SimpleTestRule)
        self.factory.register(DiagnosisTestRule)

    def test_factory_list_rules(self) -> None:
        """List all registered rules with metadata."""
        rules = self.factory.list_rules()
        self.assertEqual(len(rules), 2)
        self.assertIn("RULE-TEST-001", rules)
        self.assertIn("RULE-COND-999", rules)

    def test_factory_list_rules_metadata(self) -> None:
        """Listed rules have correct metadata."""
        rules = self.factory.list_rules()
        self.assertEqual(rules["RULE-TEST-001"].name, "Simple Test Rule")
        self.assertEqual(rules["RULE-COND-999"].category, "diagnosis")


# ============================================================================
# Test Cases: RuleInterface Contract
# ============================================================================


class TestRuleInterfaceContract(unittest.TestCase):
    """Test RuleInterface contract enforcement."""

    def test_rule_interface_abstract(self) -> None:
        """RuleInterface cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            RuleInterface()  # type: ignore

    def test_rule_must_implement_metadata_property(self) -> None:
        """Rule must implement metadata property."""

        class BadRule(RuleInterface):
            def execute(self, resources: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
                return []

        with self.assertRaises(TypeError):
            BadRule()  # type: ignore

    def test_rule_must_implement_execute_method(self) -> None:
        """Rule must implement execute method."""

        class BadRule(RuleInterface):
            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(
                    rule_id="RULE-BAD",
                    version="1.0.0",
                    name="Bad",
                    description="Bad",
                    category="test",
                )

        with self.assertRaises(TypeError):
            BadRule()  # type: ignore

    def test_rule_execute_accepts_empty_list(self) -> None:
        """Rule.execute() should handle empty resource list."""
        rule = SimpleTestRule()
        findings = rule.execute([])
        self.assertEqual(len(findings), 0)

    def test_rule_execute_returns_list(self) -> None:
        """Rule.execute() returns list."""
        rule = SimpleTestRule()
        findings = rule.execute([])
        self.assertIsInstance(findings, list)


# ============================================================================
# Test Cases: Integration
# ============================================================================


class TestIntegration(unittest.TestCase):
    """Integration tests for rule interface and factory."""

    def test_end_to_end_register_instantiate_execute(self) -> None:
        """End-to-end flow: register, instantiate, execute."""
        factory = RuleFactory()
        factory.register(SimpleTestRule)

        rule = factory.instantiate("RULE-TEST-001")
        self.assertIsInstance(rule, RuleInterface)

        findings = rule.execute([])
        self.assertIsInstance(findings, list)

    def test_multiple_rules_independent_execution(self) -> None:
        """Multiple rules execute independently."""
        factory = RuleFactory()
        factory.register(SimpleTestRule)
        factory.register(DiagnosisTestRule)

        rule1 = factory.instantiate("RULE-TEST-001")
        rule2 = factory.instantiate("RULE-COND-999")

        findings1 = rule1.execute([])
        findings2 = rule2.execute([])

        self.assertIsInstance(findings1, list)
        self.assertIsInstance(findings2, list)

    def test_factory_preserves_metadata_immutability(self) -> None:
        """Factory-instantiated rules have immutable metadata."""
        factory = RuleFactory()
        factory.register(SimpleTestRule)

        rule = factory.instantiate("RULE-TEST-001")
        metadata = rule.metadata

        # Attempt modification should raise
        with self.assertRaises((AttributeError, TypeError)):
            metadata.rule_id = "MODIFIED"  # type: ignore


# ============================================================================
# Test Cases: Edge Cases
# ============================================================================


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_metadata_version_edge_cases(self) -> None:
        """Test various valid and invalid version strings."""
        # Valid versions
        valid_versions = [
            "0.0.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0+build",
        ]
        for version in valid_versions:
            metadata = RuleMetadata(
                rule_id="RULE-TEST-001",
                version=version,
                name="Test",
                description="Test",
                category="test",
            )
            self.assertEqual(metadata.version, version)

        # Invalid versions
        invalid_versions = ["1", "1.0", "v1.0.0", "1.x.0", ""]
        for version in invalid_versions:
            with self.assertRaises(RuleVersionError):
                RuleMetadata(
                    rule_id="RULE-TEST-001",
                    version=version,
                    name="Test",
                    description="Test",
                    category="test",
                )

    def test_factory_registry_isolation(self) -> None:
        """Multiple factory instances are independent."""
        factory1 = RuleFactory()
        factory2 = RuleFactory()

        factory1.register(SimpleTestRule)

        self.assertEqual(factory1.registry_size(), 1)
        self.assertEqual(factory2.registry_size(), 0)

    def test_metadata_none_values_rejected(self) -> None:
        """None values for required fields are rejected."""
        with self.assertRaises(RuleContractError):
            RuleMetadata(
                rule_id=None,  # type: ignore
                version="1.0.0",
                name="Test",
                description="Test",
                category="test",
            )

        with self.assertRaises(RuleContractError):
            RuleMetadata(
                rule_id="RULE-TEST-001",
                version="1.0.0",
                name=None,  # type: ignore
                description="Test",
                category="test",
            )

    def test_factory_by_category_returns_new_list(self) -> None:
        """Modifying returned list doesn't affect factory state."""
        factory = RuleFactory()
        factory.register(SimpleTestRule)

        rules1 = factory.by_category("test")
        original_len = len(rules1)

        # Try to modify returned list
        rules1.append("FAKE-RULE")

        # Factory should still have original rules
        rules2 = factory.by_category("test")
        self.assertEqual(len(rules2), original_len)

    def test_factory_list_rules_returns_new_dict(self) -> None:
        """Modifying returned dict doesn't affect factory state."""
        factory = RuleFactory()
        factory.register(SimpleTestRule)

        rules1 = factory.list_rules()
        original_len = len(rules1)

        # Try to modify returned dict
        rules1["FAKE-RULE"] = RuleMetadata(
            rule_id="FAKE",
            version="1.0.0",
            name="Fake",
            description="Fake",
            category="fake",
        )

        # Factory should still have original rules
        rules2 = factory.list_rules()
        self.assertEqual(len(rules2), original_len)


if __name__ == "__main__":
    unittest.main()
