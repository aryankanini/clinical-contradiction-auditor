"""Rule pack loader with YAML deserialization, versioning, and archive management.

Provides functionality to:
- Load rule packs from YAML files with schema validation
- Manage rule pack versions and archives
- Integrate with RuleFactory for rule instantiation
- Validate semantic versioning and pack integrity
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from module_2_audit_engine.deterministic.rule_interface import (
    RuleContractError,
    RuleDuplicateError,
    RuleFactory,
)
from module_2_audit_engine.models.rule_pack import RulePack

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================


class RulePackException(Exception):
    """Base exception for rule pack loading errors."""

    pass


class RulePackParseError(RulePackException):
    """Raised when YAML parsing fails."""

    pass


class RulePackValidationError(RulePackException):
    """Raised when rule pack schema validation fails."""

    pass


class RuleDuplicateInPackError(RulePackException):
    """Raised when duplicate rule_id found in pack."""

    pass


class RulePackVersionError(RulePackException):
    """Raised when rule pack version is invalid or conflicts."""

    pass


class RulePackArchiveError(RulePackException):
    """Raised when archive operation fails."""

    pass


# ============================================================================
# Rule Pack Loader
# ============================================================================


class RulePackLoader:
    """Loads rule packs from YAML with validation and versioning.

    Provides:
    - YAML deserialization with error reporting (line numbers, parse errors)
    - Pydantic schema validation (version format, rule_id uniqueness)
    - Archive management (previous versions stored with timestamp)
    - Factory integration (rules instantiated and registered)
    - Version checking (warn if new > locked version)

    Example:
        loader = RulePackLoader(factory=factory, archive_dir=Path("data/archives"))
        pack = loader.load("data/rule_packs/rules-v1.0.0.yaml")
        loader.archive_version(pack, target_dir=Path("data/archives"))
    """

    DEFAULT_ARCHIVE_SUBDIR = "archive"
    ARCHIVE_FILENAME_FORMAT = "rule_pack-{version}-{timestamp}.yaml"

    def __init__(
        self,
        factory: RuleFactory,
        archive_dir: Optional[Path] = None,
    ) -> None:
        """Initialize loader with factory and optional archive directory.

        Args:
            factory: RuleFactory for rule registration
            archive_dir: Directory for archiving previous versions.
                        If None, defaults to parent of rule pack directory.
        """
        self.factory = factory
        self.archive_dir = archive_dir
        self._pack_cache: Optional[RulePack] = None
        logger.info(f"RulePackLoader initialized (archive_dir={archive_dir})")

    def load(self, pack_file: Path) -> RulePack:
        """Load and validate rule pack from YAML file.

        Args:
            pack_file: Path to rule pack YAML file

        Returns:
            RulePack: Deserialized and validated rule pack

        Raises:
            RulePackParseError: If YAML parsing fails
            RulePackValidationError: If schema validation fails
            RuleDuplicateInPackError: If duplicate rule_ids found
        """
        pack_file = Path(pack_file)
        logger.info(f"Loading rule pack from {pack_file}")

        # Parse YAML
        pack_data = self._parse_yaml(pack_file)

        # Validate schema
        try:
            pack = RulePack(**pack_data)
            logger.info(
                f"Successfully loaded pack {pack.metadata.pack_id} "
                f"v{pack.metadata.version} with {len(pack.rules)} rules "
                f"({len(pack.enabled_rules)} enabled)"
            )
            self._pack_cache = pack
            return pack
        except ValidationError as e:
            error_msg = self._format_validation_errors(e)
            logger.error(f"Rule pack validation failed: {error_msg}")
            raise RulePackValidationError(error_msg) from e

    def register_rules_with_factory(self, pack: RulePack) -> None:
        """Register all enabled rules from pack with factory.

        Args:
            pack: Rule pack to register

        Raises:
            RuleContractError: If rule registration fails
            RuleDuplicateError: If rule_id already registered
        """
        logger.info(
            f"Registering {len(pack.enabled_rules)} rules from pack "
            f"{pack.metadata.pack_id} with factory"
        )

        # Note: This is a placeholder for actual rule instantiation
        # In real implementation, rules would be loaded from rule modules
        # and instantiated based on rule_id, then registered with factory
        for rule_def in pack.enabled_rules:
            logger.debug(
                f"Would register rule {rule_def.rule_id} "
                f"(v{rule_def.version}, category={rule_def.category})"
            )

    def archive_version(
        self, pack: RulePack, target_dir: Optional[Path] = None
    ) -> Path:
        """Archive a rule pack version with timestamp.

        Args:
            pack: Rule pack to archive
            target_dir: Directory to store archive.
                       If None, uses loader's archive_dir.

        Returns:
            Path: Path to archived file

        Raises:
            RulePackArchiveError: If archive operation fails
        """
        if target_dir is None:
            target_dir = self.archive_dir or Path("archive")

        target_dir = Path(target_dir)
        logger.info(f"Archiving rule pack {pack.metadata.pack_id} to {target_dir}")

        try:
            # Create archive directory if needed
            target_dir.mkdir(parents=True, exist_ok=True)

            # Generate archive filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            archive_filename = self.ARCHIVE_FILENAME_FORMAT.format(
                version=pack.metadata.version, timestamp=timestamp
            )
            archive_path = target_dir / archive_filename

            # Serialize pack to YAML
            pack_dict = pack.model_dump(mode="json")
            with open(archive_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(pack_dict, f, default_flow_style=False)

            logger.info(f"Archived pack to {archive_path}")
            return archive_path
        except Exception as e:
            error_msg = f"Failed to archive rule pack: {e}"
            logger.error(error_msg)
            raise RulePackArchiveError(error_msg) from e

    def list_archived_versions(self, archive_dir: Optional[Path] = None) -> list[Path]:
        """List all archived rule pack versions.

        Args:
            archive_dir: Archive directory.
                        If None, uses loader's archive_dir.

        Returns:
            list[Path]: List of archived pack files (sorted by timestamp, newest first)
        """
        if archive_dir is None:
            archive_dir = self.archive_dir or Path("archive")

        archive_dir = Path(archive_dir)
        if not archive_dir.exists():
            return []

        # Find all archive files matching the pattern
        archives = sorted(
            archive_dir.glob("rule_pack-*.yaml"), reverse=True
        )
        logger.debug(f"Found {len(archives)} archived versions in {archive_dir}")
        return archives

    def check_version(
        self,
        new_pack: RulePack,
        locked_version: Optional[str] = None,
    ) -> bool:
        """Check new pack version against locked version.

        Args:
            new_pack: New rule pack to check
            locked_version: Locked version string (e.g., "1.0.0").
                           If None, check skipped.

        Returns:
            bool: True if new version >= locked version (or no lock)
                  False if new version < locked version

        Note:
            Logs WARNING if new version < locked version.
        """
        if locked_version is None:
            logger.debug("No locked version; version check skipped")
            return True

        new_ver = self._parse_version(new_pack.metadata.version)
        locked_ver = self._parse_version(locked_version)

        if new_ver >= locked_ver:
            logger.info(
                f"Version check passed: {new_pack.metadata.version} >= {locked_version}"
            )
            return True
        else:
            logger.warning(
                f"Version check WARNING: new pack version "
                f"{new_pack.metadata.version} < locked {locked_version}"
            )
            return False

    @staticmethod
    def _parse_yaml(pack_file: Path) -> dict[str, Any]:
        """Parse YAML file with error reporting.

        Args:
            pack_file: Path to YAML file

        Returns:
            dict[str, Any]: Parsed YAML data

        Raises:
            RulePackParseError: If parsing fails
        """
        try:
            with open(pack_file, "r", encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f)
            if data is None:
                raise RulePackParseError(f"Empty YAML file: {pack_file}")
            logger.debug(f"Successfully parsed YAML: {pack_file}")
            return data
        except yaml.YAMLError as e:
            error_msg = f"YAML parse error in {pack_file}: {e}"
            logger.error(error_msg)
            raise RulePackParseError(error_msg) from e
        except OSError as e:
            error_msg = f"Cannot read file {pack_file}: {e}"
            logger.error(error_msg)
            raise RulePackParseError(error_msg) from e

    @staticmethod
    def _format_validation_errors(error: ValidationError) -> str:
        """Format Pydantic validation errors for logging.

        Args:
            error: Pydantic ValidationError

        Returns:
            str: Formatted error message
        """
        errors = error.errors()
        formatted = []
        for err in errors:
            location = " → ".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            formatted.append(f"{location}: {msg}")
        return "; ".join(formatted)

    @staticmethod
    def _parse_version(version_str: str) -> tuple[int, int, int]:
        """Parse semantic version string to comparable tuple.

        Args:
            version_str: Version string (e.g., "1.2.3")

        Returns:
            tuple: (major, minor, patch) as integers

        Raises:
            RulePackVersionError: If version format is invalid
        """
        try:
            parts = version_str.split(".")[0:3]
            if len(parts) != 3:
                raise ValueError("Invalid semver format")
            major, minor, patch = [int(p) for p in parts]
            return (major, minor, patch)
        except (ValueError, TypeError) as e:
            raise RulePackVersionError(
                f"Invalid semantic version {version_str}: {e}"
            ) from e


# ============================================================================
# Archive Manager (convenience class)
# ============================================================================


class ArchiveManager:
    """Manages rule pack versioning and archival.

    Provides utilities for organizing, listing, and retrieving
    archived rule pack versions.
    """

    def __init__(self, archive_dir: Path) -> None:
        """Initialize archive manager.

        Args:
            archive_dir: Root archive directory
        """
        self.archive_dir = Path(archive_dir)
        logger.info(f"ArchiveManager initialized (root={archive_dir})")

    def cleanup_old_versions(self, keep_count: int = 5) -> int:
        """Clean up old archived versions, keeping only N most recent.

        Args:
            keep_count: Number of recent versions to keep

        Returns:
            int: Number of files deleted

        Raises:
            RulePackArchiveError: If cleanup fails
        """
        logger.info(
            f"Cleaning up archives in {self.archive_dir}, keeping {keep_count} recent"
        )

        try:
            archives = sorted(
                self.archive_dir.glob("rule_pack-*.yaml"), reverse=True
            )
            to_delete = archives[keep_count:]
            deleted_count = 0

            for archive_file in to_delete:
                try:
                    archive_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted archive: {archive_file}")
                except OSError as e:
                    logger.warning(f"Failed to delete {archive_file}: {e}")

            logger.info(f"Deleted {deleted_count} old archive files")
            return deleted_count
        except Exception as e:
            error_msg = f"Archive cleanup failed: {e}"
            logger.error(error_msg)
            raise RulePackArchiveError(error_msg) from e
