"""Pytest configuration and fixtures for rule engine tests.

Provides shared fixtures for unit and integration tests:
- Rule factory with test rules
- Sample rule packs (YAML data)
- Mock FHIR resources
- Audit log fixtures
"""

from __future__ import annotations

import logging
import pytest
from pathlib import Path
from typing import Any, List, Mapping
from unittest.mock import MagicMock

from module_2_audit_engine.deterministic.rule_interface import (
    RuleFactory,
    RuleInterface,
    RuleMetadata,
)
from module_2_audit_engine.deterministic.safety_validator import SafetyValidator
from module_2_audit_engine.deterministic.audit_log import AppendOnlyAuditLog
from module_2_audit_engine.deterministic.orchestrator import RuleOrchestrator
from module_2_audit_engine.models.rule_pack import (
    RulePack,
    RulePackMetadata,
    RuleDefinition,
)


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config: Any) -> None:
    """Configure pytest and logging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s [%(name)s] %(message)s",
    )


# ============================================================================
# Test Rule Implementations
# ============================================================================


class TestRuleAlwaysPass(RuleInterface):
    """Test rule that always passes (no findings)."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="TEST-PASS-001",
            version="1.0.0",
            name="Always Pass Rule",
            category="test",
            description="Test rule that finds no contradictions",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(
        self, resources: List[Mapping[str, Any]]
    ) -> List[Mapping[str, Any]]:
        """Return no findings (rule passes)."""
        return []


class TestRuleWithFinding(RuleInterface):
    """Test rule that always emits one finding."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="TEST-FIND-001",
            version="1.0.0",
            name="Finding Rule",
            category="test",
            description="Test rule that finds one contradiction",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(
        self, resources: List[Mapping[str, Any]]
    ) -> List[Mapping[str, Any]]:
        """Return one safe finding."""
        return [
            {
                "rule_id": "TEST-FIND-001",
                "severity": "warning",
                "category": "test",
                "narrative": "Test contradiction detected",
                "evidence": [
                    {"field": "code", "value": "test-code"}
                ],
                "status": "active",
            }
        ]


class TestRuleWithException(RuleInterface):
    """Test rule that raises an exception."""

    def __init__(self) -> None:
        self._metadata = RuleMetadata(
            rule_id="TEST-ERROR-001",
            version="1.0.0",
            name="Error Rule",
            category="test",
            description="Test rule that raises an exception",
        )

    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata

    def execute(
        self, resources: List[Mapping[str, Any]]
    ) -> List[Mapping[str, Any]]:
        """Raise an exception during execution."""
        raise ValueError("Simulated rule execution error")


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def rule_factory() -> RuleFactory:
    """Create a rule factory with test rules registered."""
    factory = RuleFactory()
    factory.register(TestRuleAlwaysPass)
    factory.register(TestRuleWithFinding)
    factory.register(TestRuleWithException)
    return factory


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_rule_pack() -> RulePack:
    """Create a sample rule pack for testing."""
    metadata = RulePackMetadata(
        pack_id="test-pack-001",
        version="1.0.0",
        description="Test rule pack with 3 rules",
    )
    
    definitions = [
        RuleDefinition(
            rule_id="TEST-PASS-001",
            version="1.0.0",
            name="Always Pass Rule",
            category="test",
            description="Test rule that finds no contradictions",
        ),
        RuleDefinition(
            rule_id="TEST-FIND-001",
            version="1.0.0",
            name="Finding Rule",
            category="test",
            description="Test rule that finds one contradiction",
        ),
        RuleDefinition(
            rule_id="TEST-ERROR-001",
            version="1.0.0",
            name="Error Rule",
            category="test",
            description="Test rule that raises an exception",
        ),
    ]
    
    return RulePack(metadata=metadata, rules=definitions)


@pytest.fixture
def mock_fhir_patient() -> Mapping[str, Any]:
    """Create a mock FHIR Patient resource for testing."""
    return {
        "resourceType": "Patient",
        "id": "patient-001",
        "name": [{"given": ["John"], "family": "Doe"}],
        "birthDate": "1980-01-01",
        "gender": "male",
    }


@pytest.fixture
def mock_fhir_condition() -> Mapping[str, Any]:
    """Create a mock FHIR Condition resource for testing."""
    return {
        "resourceType": "Condition",
        "id": "cond-001",
        "subject": {"reference": "Patient/patient-001"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "123456",
                    "display": "Test Condition",
                }
            ]
        },
        "status": "active",
        "onsetDateTime": "2020-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_fhir_medication() -> Mapping[str, Any]:
    """Create a mock FHIR Medication resource for testing."""
    return {
        "resourceType": "Medication",
        "id": "med-001",
        "code": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "12345",
                    "display": "Test Medication",
                }
            ]
        },
        "status": "active",
    }


@pytest.fixture
def mock_fhir_medication_statement() -> Mapping[str, Any]:
    """Create a mock FHIR MedicationStatement resource for testing."""
    return {
        "resourceType": "MedicationStatement",
        "id": "medstmt-001",
        "subject": {"reference": "Patient/patient-001"},
        "medicationReference": {"reference": "Medication/med-001"},
        "status": "active",
        "effectiveDatetime": "2020-01-01T00:00:00Z",
        "dosage": [
            {
                "route": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "26643006",
                            "display": "Oral route",
                        }
                    ]
                },
                "doseQuantity": {"value": 500, "unit": "mg"},
            }
        ],
    }


@pytest.fixture
def sample_patient_resources() -> Mapping[str, Any]:
    """Create a complete sample patient resource bundle for testing."""
    return {
        "Patient": {
            "resourceType": "Patient",
            "id": "patient-001",
            "name": [{"given": ["Jane"], "family": "Smith"}],
            "birthDate": "1975-05-15",
            "gender": "female",
        },
        "Condition": [
            {
                "resourceType": "Condition",
                "id": "cond-001",
                "subject": {"reference": "Patient/patient-001"},
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "73211009",
                            "display": "Diabetes mellitus",
                        }
                    ]
                },
                "status": "active",
                "onsetDateTime": "2015-01-01T00:00:00Z",
            },
            {
                "resourceType": "Condition",
                "id": "cond-002",
                "subject": {"reference": "Patient/patient-001"},
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "38341003",
                            "display": "Hypertension",
                        }
                    ]
                },
                "status": "active",
                "onsetDateTime": "2018-06-15T00:00:00Z",
            },
        ],
        "MedicationStatement": [
            {
                "resourceType": "MedicationStatement",
                "id": "medstmt-001",
                "subject": {"reference": "Patient/patient-001"},
                "medicationReference": {"reference": "Medication/med-001"},
                "status": "active",
                "effectiveDatetime": "2020-01-01T00:00:00Z",
                "dosage": [
                    {
                        "route": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "26643006",
                                    "display": "Oral route",
                                }
                            ]
                        },
                        "doseQuantity": {"value": 1000, "unit": "mg"},
                        "timing": {"repeat": {"frequency": 2, "period": 1}},
                    }
                ],
            }
        ],
    }


@pytest.fixture
def safety_validator() -> SafetyValidator:
    """Create a safety validator for testing."""
    # Create from YAML if it exists, otherwise use in-memory keywords
    yaml_path = Path(__file__).parent.parent / "data" / "safety_keywords.yaml"
    if yaml_path.exists():
        return SafetyValidator.from_yaml_file(str(yaml_path))
    else:
        # Fallback: create with basic keywords
        keywords = [
            "diagnose",
            "diagnosis",
            "treat",
            "treatment",
            "prescribe",
            "prescription",
            "recommend",
            "recommendation",
        ]
        return SafetyValidator(keywords=keywords)


@pytest.fixture
def audit_log() -> AppendOnlyAuditLog:
    """Create a fresh append-only audit log for testing."""
    return AppendOnlyAuditLog()


@pytest.fixture
def orchestrator(
    rule_factory: RuleFactory, safety_validator: SafetyValidator
) -> RuleOrchestrator:
    """Create a rule orchestrator with test factory and safety validator."""
    return RuleOrchestrator(factory=rule_factory)
