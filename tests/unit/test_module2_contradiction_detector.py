from __future__ import annotations

import unittest
from datetime import datetime, timezone

from module_2_audit_engine.contradiction_detector import ContradictionDetector
from tests.unit.api_test_base import audit_input


class ContradictionDetectorTests(unittest.TestCase):
    def test_detector_reports_non_placeholder_engine(self) -> None:
        detector = ContradictionDetector()

        self.assertFalse(detector.is_placeholder)

    def test_detector_emits_expected_condition_finding(self) -> None:
        detector = ContradictionDetector(as_of=datetime(2026, 8, 25, tzinfo=timezone.utc))
        records = [
            audit_input(
                "cond-1",
                "Condition",
                "active",
                timestamps={"onsetDateTime": "2026-09-01T00:00:00Z"},
            )
        ]

        result = detector.evaluate_batch(records, {"version": "2.1.0"})

        self.assertEqual(result.rule_pack_version, "2.1.0")
        self.assertEqual(result.evaluated_record_count, 1)
        self.assertIn("RULE-COND-001", {finding.rule_id for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
