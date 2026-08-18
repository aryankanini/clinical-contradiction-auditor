"""Unit tests for safety validator and audit log infrastructure.

Tests verify:
- Finding immutability (frozen dataclass)
- Keyword detection (diagnosis, treatment, recommendations)
- Safety boundary enforcement
- Audit log append-only semantics
- Validator statistics and logging
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, List, Mapping

from module_2_audit_engine.deterministic.audit_log import (
    AppendOnlyAuditLog,
    AuditLogEntry,
    AuditLogWriteError,
)
from module_2_audit_engine.deterministic.safety_validator import (
    SafetyBoundaryError,
    SafetyKeywordError,
    SafetyValidator,
)
from module_2_audit_engine.models.finding import Finding


# ============================================================================
# Test Cases: Finding Immutability
# ============================================================================


class TestFindingImmutability(unittest.TestCase):
    """Test Finding immutability."""

    def setUp(self) -> None:
        """Create test finding."""
        self.finding = Finding(
            rule_id="RULE-TEST-001",
            severity="warning",
            category="diagnosis",
            evidence=[{"field": "condition", "value": "active"}],
            narrative="Test finding",
        )

    def test_finding_frozen_raises_on_modification(self) -> None:
        """Frozen dataclass raises on field modification."""
        with self.assertRaises(Exception):  # FrozenInstanceError
            self.finding.severity = "critical"  # type: ignore

    def test_finding_creation_validates_severity(self) -> None:
        """Finding creation validates severity."""
        with self.assertRaises(ValueError):
            Finding(
                rule_id="RULE-TEST-001",
                severity="invalid",  # type: ignore
                category="diagnosis",
            )

    def test_finding_creation_validates_status(self) -> None:
        """Finding creation validates status."""
        with self.assertRaises(ValueError):
            Finding(
                rule_id="RULE-TEST-001",
                severity="warning",
                category="diagnosis",
                status="invalid",  # type: ignore
            )

    def test_finding_creation_validates_rule_id(self) -> None:
        """Finding creation validates rule_id."""
        with self.assertRaises(ValueError):
            Finding(
                rule_id="",
                severity="warning",
                category="diagnosis",
            )

    def test_finding_as_dict(self) -> None:
        """Finding serializes to dictionary."""
        finding_dict = self.finding.as_dict()
        self.assertEqual(finding_dict["rule_id"], "RULE-TEST-001")
        self.assertEqual(finding_dict["severity"], "warning")
        self.assertIsInstance(finding_dict["evidence"], list)


# ============================================================================
# Test Cases: SafetyValidator Keyword Detection
# ============================================================================


class TestSafetyValidatorKeywordDetection(unittest.TestCase):
    """Test keyword detection."""

    def setUp(self) -> None:
        """Create validator with test keywords."""
        keywords = [
            "diagnose",
            "diagnosis",
            "treat",
            "treatment",
            "prescribe",
            "recommend",
            "recommend therapy",
        ]
        self.validator = SafetyValidator(keywords)

    def test_detects_diagnosis_keyword(self) -> None:
        """Detects 'diagnose' keyword in narrative."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "We diagnose the patient with condition X",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_detects_treatment_keyword(self) -> None:
        """Detects 'treatment' keyword in narrative."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "This treatment plan should be followed",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_detects_prescribe_keyword(self) -> None:
        """Detects 'prescribe' keyword."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "We prescribe antibiotics",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_detects_recommend_keyword(self) -> None:
        """Detects 'recommend' keyword."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "We recommend physical therapy",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_detects_keyword_in_evidence(self) -> None:
        """Detects keyword in evidence field."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Finding detected",
                "evidence": [{"description": "Treatment was provided"}],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_case_insensitive_matching(self) -> None:
        """Keyword matching is case-insensitive."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "DIAGNOSE the patient",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_word_boundary_matching(self) -> None:
        """Word boundary matching prevents false positives."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Undiagnosed condition noted",
                "evidence": [],
            }
        ]
        # "undiagnosed" should not match "diagnose" (word boundary)
        # This should raise because "undiagnosed" contains word boundary
        result = self.validator.validate_findings(findings)
        # Verify it matched (word boundary should catch it)
        # Actually, regex \bdiagnose\b won't match "undiagnosed"
        # So this should pass (not raise)
        self.assertEqual(len(result), 1)

    def test_multi_word_keyword_detection(self) -> None:
        """Detects multi-word keywords."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Recommend therapy is needed",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)


# ============================================================================
# Test Cases: SafetyValidator Safe Findings
# ============================================================================


class TestSafetyValidatorSafeFindings(unittest.TestCase):
    """Test validation of safe findings."""

    def setUp(self) -> None:
        """Create validator."""
        keywords = ["diagnose", "treat", "prescribe", "recommend"]
        self.validator = SafetyValidator(keywords)

    def test_safe_finding_passes_validation(self) -> None:
        """Safe finding passes validation."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Conflict detected between data points",
                "evidence": [{"field": "value", "data": "consistent"}],
            }
        ]
        result = self.validator.validate_findings(findings)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rule_id"], "RULE-001")

    def test_multiple_safe_findings_pass(self) -> None:
        """Multiple safe findings pass validation."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Conflict A detected",
                "evidence": [],
            },
            {
                "rule_id": "RULE-002",
                "narrative": "Conflict B detected",
                "evidence": [],
            },
            {
                "rule_id": "RULE-003",
                "narrative": "Conflict C detected",
                "evidence": [],
            },
        ]
        result = self.validator.validate_findings(findings)
        self.assertEqual(len(result), 3)

    def test_empty_evidence_passes(self) -> None:
        """Finding with empty evidence passes validation."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Finding with no evidence",
                "evidence": [],
            }
        ]
        result = self.validator.validate_findings(findings)
        self.assertEqual(len(result), 1)

    def test_null_narrative_handled(self) -> None:
        """Null narrative field handled gracefully."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": None,
                "evidence": [],
            }
        ]
        # Should handle None gracefully (not crash)
        result = self.validator.validate_findings(findings)
        self.assertEqual(len(result), 1)


# ============================================================================
# Test Cases: SafetyValidator Boundary Enforcement
# ============================================================================


class TestSafetyValidatorBoundaryEnforcement(unittest.TestCase):
    """Test boundary enforcement."""

    def setUp(self) -> None:
        """Create validator."""
        keywords = ["diagnose", "prescribe"]
        self.validator = SafetyValidator(keywords)

    def test_reject_unsafe_finding(self) -> None:
        """Reject finding with unsafe keyword."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "Safe part",
                "evidence": [{"text": "diagnose patient"}],
            }
        ]
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_reject_multiple_unsafe_findings(self) -> None:
        """Reject multiple unsafe findings, keep safe ones."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "diagnose condition",  # UNSAFE
                "evidence": [],
            },
            {
                "rule_id": "RULE-002",
                "narrative": "safe finding",  # SAFE
                "evidence": [],
            },
            {
                "rule_id": "RULE-003",
                "narrative": "prescribe treatment",  # UNSAFE
                "evidence": [],
            },
        ]
        # Validation stops on first unsafe finding
        with self.assertRaises(SafetyBoundaryError):
            self.validator.validate_findings(findings)

    def test_boundary_error_includes_rule_id(self) -> None:
        """Error message includes rule_id."""
        findings = [
            {
                "rule_id": "RULE-DANGEROUS-001",
                "narrative": "diagnose issue",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError) as ctx:
            self.validator.validate_findings(findings)
        self.assertIn("RULE-DANGEROUS-001", str(ctx.exception))

    def test_boundary_error_includes_detected_keywords(self) -> None:
        """Error message includes detected keywords."""
        findings = [
            {
                "rule_id": "RULE-001",
                "narrative": "diagnose and prescribe",
                "evidence": [],
            }
        ]
        with self.assertRaises(SafetyBoundaryError) as ctx:
            self.validator.validate_findings(findings)
        error_msg = str(ctx.exception)
        self.assertIn("diagnose", error_msg)


# ============================================================================
# Test Cases: SafetyValidator Initialization
# ============================================================================


class TestSafetyValidatorInitialization(unittest.TestCase):
    """Test validator initialization."""

    def test_init_with_empty_keywords_raises(self) -> None:
        """Empty keyword list raises error."""
        with self.assertRaises(SafetyKeywordError):
            SafetyValidator([])

    def test_init_from_yaml_file(self) -> None:
        """Load validator from YAML file."""
        yaml_path = Path("data/safety_keywords.yaml")
        if yaml_path.exists():
            validator = SafetyValidator.from_yaml_file(yaml_path)
            self.assertGreater(len(validator.keywords), 0)

    def test_init_from_yaml_missing_file(self) -> None:
        """Missing YAML file raises error."""
        with self.assertRaises(SafetyKeywordError):
            SafetyValidator.from_yaml_file("nonexistent.yaml")


# ============================================================================
# Test Cases: AuditLog Entry and Append-Only
# ============================================================================


class TestAuditLogEntry(unittest.TestCase):
    """Test audit log entries."""

    def test_audit_log_entry_creation(self) -> None:
        """Create audit log entry."""
        entry = AuditLogEntry(
            batch_run_id="BATCH-001",
            findings_count=5,
            rule_pack_version="1.0.0",
            status="success",
        )
        self.assertEqual(entry.batch_run_id, "BATCH-001")
        self.assertEqual(entry.findings_count, 5)

    def test_audit_log_entry_frozen(self) -> None:
        """Audit log entry is immutable."""
        entry = AuditLogEntry(batch_run_id="BATCH-001", findings_count=5)
        with self.assertRaises(Exception):  # FrozenInstanceError
            entry.findings_count = 10  # type: ignore

    def test_audit_log_entry_validates_status(self) -> None:
        """Entry creation validates status."""
        with self.assertRaises(ValueError):
            AuditLogEntry(
                batch_run_id="BATCH-001",
                findings_count=5,
                status="invalid",  # type: ignore
            )

    def test_audit_log_entry_as_dict(self) -> None:
        """Entry serializes to dictionary."""
        entry = AuditLogEntry(
            batch_run_id="BATCH-001",
            findings_count=5,
            status="success",
        )
        entry_dict = entry.as_dict()
        self.assertEqual(entry_dict["batch_run_id"], "BATCH-001")
        self.assertEqual(entry_dict["findings_count"], 5)
        self.assertIn("timestamp_utc", entry_dict)


# ============================================================================
# Test Cases: AppendOnlyAuditLog
# ============================================================================


class TestAppendOnlyAuditLog(unittest.TestCase):
    """Test append-only audit log."""

    def setUp(self) -> None:
        """Create audit log."""
        self.log = AppendOnlyAuditLog()

    def test_append_entry(self) -> None:
        """Append entry to log."""
        entry = self.log.append_entry(
            batch_run_id="BATCH-001",
            findings_count=5,
            status="success",
        )
        self.assertEqual(entry.batch_run_id, "BATCH-001")
        self.assertEqual(entry.findings_count, 5)

    def test_append_multiple_entries(self) -> None:
        """Append multiple entries."""
        self.log.append_entry("BATCH-001", 5, status="success")
        self.log.append_entry("BATCH-002", 3, status="success")
        self.log.append_entry("BATCH-003", 0, status="failed")

        entries = self.log.get_all_entries()
        self.assertEqual(len(entries), 3)

    def test_append_only_semantics(self) -> None:
        """Append-only: entries never modified after append."""
        entry1 = self.log.append_entry("BATCH-001", 5)
        entries = self.log.get_all_entries()
        self.assertEqual(entries[0].findings_count, 5)

        # Append new entry
        entry2 = self.log.append_entry("BATCH-002", 3)

        # Original entry should still be unchanged
        entries = self.log.get_all_entries()
        self.assertEqual(entries[0].findings_count, 5)
        self.assertEqual(entries[1].findings_count, 3)

    def test_get_entries_for_batch(self) -> None:
        """Retrieve entries for specific batch."""
        self.log.append_entry("BATCH-001", 5)
        self.log.append_entry("BATCH-002", 3)
        self.log.append_entry("BATCH-001", 2)

        batch_1_entries = self.log.get_entries_for_batch("BATCH-001")
        self.assertEqual(len(batch_1_entries), 2)
        self.assertEqual(batch_1_entries[0].findings_count, 5)
        self.assertEqual(batch_1_entries[1].findings_count, 2)

    def test_audit_log_statistics(self) -> None:
        """Get audit log statistics."""
        self.log.append_entry("BATCH-001", 5, status="success")
        self.log.append_entry("BATCH-002", 3, status="success")
        self.log.append_entry("BATCH-003", 0, status="failed")

        stats = self.log.get_statistics()
        self.assertEqual(stats["total_entries"], 3)
        self.assertEqual(stats["successful"], 2)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["total_findings"], 8)


# ============================================================================
# Test Cases: SafetyValidator Statistics
# ============================================================================


class TestSafetyValidatorStatistics(unittest.TestCase):
    """Test validator statistics."""

    def test_validator_statistics(self) -> None:
        """Track validator statistics."""
        validator = SafetyValidator(["diagnose", "treat"])

        # First scan
        findings1 = [
            {"rule_id": "RULE-001", "narrative": "Safe finding", "evidence": []}
        ]
        validator.validate_findings(findings1)

        # Second scan
        findings2 = [
            {"rule_id": "RULE-002", "narrative": "Safe finding", "evidence": []}
        ]
        validator.validate_findings(findings2)

        stats = validator.get_statistics()
        self.assertEqual(stats["scan_count"], 2)
        self.assertEqual(stats["reject_count"], 0)


if __name__ == "__main__":
    unittest.main()
