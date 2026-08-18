"""Safety boundary validator for audit findings.

Enforces safety boundaries to prevent diagnostic keywords and treatment
recommendations in findings. Implements wrap-around validation for orchestrator
output before emission.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List, Mapping

import yaml

logger = logging.getLogger(__name__)


class SafetyBoundaryError(Exception):
    """Raised when a finding violates safety boundaries."""

    pass


class SafetyKeywordError(Exception):
    """Raised when safety keywords cannot be loaded."""

    pass


class SafetyValidator:
    """Validates findings against safety boundaries.

    Enforces audit compliance by preventing diagnostic keywords and treatment
    recommendations in findings. Implements keyword scanning with full-text
    search and boundary enforcement.

    Attributes:
        keywords: List of unsafe keywords (case-insensitive)
        strict_mode: If True, any keyword match fails; if False, whitelist-aware

    Example:
        >>> validator = SafetyValidator.from_yaml_file("keywords.yaml")
        >>> findings = [{"narrative": "Patient has diagnosis"}]
        >>> try:
        ...     validator.validate_findings(findings)
        ... except SafetyBoundaryError as e:
        ...     print(f"Validation failed: {e}")
    """

    def __init__(self, keywords: List[str], strict_mode: bool = True) -> None:
        """Initialize validator with keyword list.

        Args:
            keywords: List of unsafe keywords
            strict_mode: If True, any keyword match fails

        Raises:
            SafetyKeywordError: If keyword list empty
        """
        if not keywords:
            raise SafetyKeywordError("Keyword list cannot be empty")

        self.keywords = [kw.lower() for kw in keywords]
        self.strict_mode = strict_mode
        self.scan_count = 0
        self.reject_count = 0

        logger.info(
            f"SafetyValidator initialized with {len(self.keywords)} keywords, "
            f"strict_mode={strict_mode}"
        )

    @staticmethod
    def from_yaml_file(
        filepath: str | Path, strict_mode: bool = True
    ) -> SafetyValidator:
        """Load keywords from YAML configuration file.

        Args:
            filepath: Path to safety keywords YAML file
            strict_mode: If True, enforce strict boundary checking

        Returns:
            SafetyValidator: Initialized validator

        Raises:
            SafetyKeywordError: If file not found or invalid YAML
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise SafetyKeywordError(f"Keywords file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SafetyKeywordError(f"Failed to parse YAML: {e}")

        if not config or "all_keywords" not in config:
            raise SafetyKeywordError(
                "Keywords file missing 'all_keywords' section"
            )

        keywords = config["all_keywords"]
        if not keywords:
            raise SafetyKeywordError("'all_keywords' list is empty")

        logger.info(f"Loaded {len(keywords)} keywords from {filepath}")
        return SafetyValidator(keywords, strict_mode=strict_mode)

    def validate_findings(
        self, findings: List[Mapping[str, Any]]
    ) -> List[Mapping[str, Any]]:
        """Validate findings against safety boundaries.

        Scans all findings for unsafe keywords in evidence and narrative fields.
        Raises exception if any finding violates boundaries.

        Args:
            findings: List of findings to validate

        Returns:
            List[Mapping[str, Any]]: Validated findings (if all pass)

        Raises:
            SafetyBoundaryError: If any finding violates boundaries
        """
        self.scan_count += 1
        logger.info(f"Validating {len(findings)} findings (scan #{self.scan_count})")

        for i, finding in enumerate(findings):
            try:
                self._validate_single_finding(finding)
                logger.debug(f"Finding {i}: PASS")
            except SafetyBoundaryError as e:
                self.reject_count += 1
                logger.warning(f"Finding {i}: REJECTED - {e}")
                raise

        logger.info(
            f"Validation complete: {len(findings)} findings passed validation"
        )

        return list(findings)

    def _validate_single_finding(self, finding: Mapping[str, Any]) -> None:
        """Validate single finding against safety boundaries.

        Scans narrative and evidence fields for unsafe keywords.

        Args:
            finding: Finding to validate

        Raises:
            SafetyBoundaryError: If finding contains unsafe keywords
        """
        narrative = finding.get("narrative", "")
        if narrative:
            self._scan_text(narrative, "narrative", finding)

        evidence = finding.get("evidence", [])
        if evidence:
            for i, evidence_item in enumerate(evidence):
                if isinstance(evidence_item, Mapping):
                    for key, value in evidence_item.items():
                        if isinstance(value, str):
                            self._scan_text(
                                value, f"evidence[{i}].{key}", finding
                            )

    def _scan_text(
        self,
        text: str,
        field_name: str,
        finding: Mapping[str, Any],
    ) -> None:
        """Scan text for unsafe keywords.

        Case-insensitive search for keywords in text.

        Args:
            text: Text to scan
            field_name: Name of field being scanned (for logging)
            finding: Original finding (for context)

        Raises:
            SafetyBoundaryError: If unsafe keywords found
        """
        text_lower = text.lower()

        detected_keywords = []
        for keyword in self.keywords:
            # Word boundary matching (case-insensitive)
            if self._keyword_match(text_lower, keyword):
                detected_keywords.append(keyword)

        if detected_keywords:
            rule_id = finding.get("rule_id", "UNKNOWN")
            raise SafetyBoundaryError(
                f"Unsafe keywords in {field_name} for {rule_id}: "
                f"{', '.join(detected_keywords)}"
            )

    @staticmethod
    def _keyword_match(text: str, keyword: str) -> bool:
        """Check if keyword matches in text (word boundary).

        Matches whole words only (word boundary matching).

        Args:
            text: Text to search in
            keyword: Keyword to search for

        Returns:
            bool: True if keyword found as whole word
        """
        pattern = rf"\b{re.escape(keyword)}\b"
        return bool(re.search(pattern, text))

    def get_statistics(self) -> dict[str, Any]:
        """Get validator statistics.

        Returns:
            dict[str, Any]: Statistics including scan count, rejection count
        """
        return {
            "keyword_count": len(self.keywords),
            "scan_count": self.scan_count,
            "reject_count": self.reject_count,
            "rejection_rate": (
                self.reject_count / self.scan_count
                if self.scan_count > 0
                else 0.0
            ),
        }
