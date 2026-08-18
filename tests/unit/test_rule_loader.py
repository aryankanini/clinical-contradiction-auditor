"""Unit tests for rule pack loader and YAML deserialization.

Tests verify:
- YAML parsing with error handling
- Schema validation (version format, rule_id uniqueness)
- Archive creation and retrieval
- Version checking
- Factory integration
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

from module_2_audit_engine.deterministic.rule_interface import RuleFactory
from module_2_audit_engine.deterministic.rule_loader import (
    ArchiveManager,
    RulePackArchiveError,
    RulePackLoader,
    RulePackParseError,
    RulePackValidationError,
)
from module_2_audit_engine.models.rule_pack import (
    RuleDefinition,
    RulePack,
    RulePackMetadata,
)


# ============================================================================
# Test Rule Pack Fixtures
# ============================================================================


def create_valid_pack() -> RulePack:
    """Create a valid test rule pack."""
    return RulePack(
        metadata=RulePackMetadata(
            pack_id="PACK-TEST-001",
            version="1.0.0",
            description="Test pack",
            author="Test Author",
            organization="Test Org",
        ),
        rules=[
            RuleDefinition(
                rule_id="RULE-TEST-001",
                version="1.0.0",
                name="Test Rule 1",
                description="Test rule 1",
                category="test",
            ),
            RuleDefinition(
                rule_id="RULE-TEST-002",
                version="1.0.0",
                name="Test Rule 2",
                description="Test rule 2",
                category="test",
            ),
        ],
    )


def create_invalid_yaml(temp_dir: Path) -> Path:
    """Create invalid YAML file."""
    yaml_file = temp_dir / "invalid.yaml"
    with open(yaml_file, "w") as f:
        f.write("invalid: yaml: content:\n  - bad indentation\n    - very bad")
    return yaml_file


def create_valid_yaml(temp_dir: Path, pack: RulePack | None = None) -> Path:
    """Create valid YAML file from rule pack."""
    if pack is None:
        pack = create_valid_pack()

    yaml_file = temp_dir / f"pack-{pack.metadata.version}.yaml"
    pack_dict = pack.model_dump(mode="json")
    with open(yaml_file, "w") as f:
        yaml.safe_dump(pack_dict, f, default_flow_style=False)
    return yaml_file


# ============================================================================
# Test Cases: RulePack Schema
# ============================================================================


class TestRulePackSchema(unittest.TestCase):
    """Test RulePack Pydantic schema validation."""

    def test_rule_pack_creation_valid(self) -> None:
        """Create valid rule pack."""
        pack = create_valid_pack()
        self.assertEqual(pack.metadata.pack_id, "PACK-TEST-001")
        self.assertEqual(len(pack.rules), 2)

    def test_rule_pack_frozen(self) -> None:
        """Rule pack is immutable."""
        from pydantic import ValidationError

        pack = create_valid_pack()
        with self.assertRaises(ValidationError):
            pack.metadata = RulePackMetadata(  # type: ignore
                pack_id="NEW-PACK",
                version="1.0.0",
            )

    def test_rule_pack_duplicate_rule_ids_rejected(self) -> None:
        """Duplicate rule_ids in pack are rejected."""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            RulePack(
                metadata=RulePackMetadata(
                    pack_id="PACK-TEST-001",
                    version="1.0.0",
                ),
                rules=[
                    RuleDefinition(
                        rule_id="RULE-TEST-001",
                        version="1.0.0",
                        name="Test Rule 1",
                        description="Test rule 1",
                        category="test",
                    ),
                    RuleDefinition(
                        rule_id="RULE-TEST-001",  # Duplicate!
                        version="1.0.0",
                        name="Test Rule 2",
                        description="Test rule 2",
                        category="test",
                    ),
                ],
            )

    def test_rule_pack_enabled_rules(self) -> None:
        """Get only enabled rules."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-TEST-001",
                version="1.0.0",
            ),
            rules=[
                RuleDefinition(
                    rule_id="RULE-TEST-001",
                    version="1.0.0",
                    name="Test Rule 1",
                    description="Test rule 1",
                    category="test",
                    enabled=True,
                ),
                RuleDefinition(
                    rule_id="RULE-TEST-002",
                    version="1.0.0",
                    name="Test Rule 2",
                    description="Test rule 2",
                    category="test",
                    enabled=False,
                ),
            ],
        )
        enabled = pack.enabled_rules
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].rule_id, "RULE-TEST-001")

    def test_rule_pack_rule_id_to_definition_mapping(self) -> None:
        """Create rule_id to definition mapping."""
        pack = create_valid_pack()
        mapping = pack.rule_id_to_definition
        self.assertEqual(len(mapping), 2)
        self.assertIn("RULE-TEST-001", mapping)
        self.assertEqual(
            mapping["RULE-TEST-001"].name, "Test Rule 1"
        )


# ============================================================================
# Test Cases: Rule Pack Loader
# ============================================================================


class TestRulePackLoader(unittest.TestCase):
    """Test RulePackLoader YAML parsing and validation."""

    def setUp(self) -> None:
        """Create temp directory and loader."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.factory = RuleFactory()
        self.loader = RulePackLoader(
            factory=self.factory,
            archive_dir=self.temp_path / "archive",
        )

    def tearDown(self) -> None:
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_loader_load_valid_pack(self) -> None:
        """Load valid rule pack from YAML."""
        pack = create_valid_pack()
        yaml_file = create_valid_yaml(self.temp_path, pack)

        loaded = self.loader.load(yaml_file)
        self.assertEqual(loaded.metadata.pack_id, "PACK-TEST-001")
        self.assertEqual(len(loaded.rules), 2)

    def test_loader_load_invalid_yaml(self) -> None:
        """Reject invalid YAML syntax."""
        yaml_file = create_invalid_yaml(self.temp_path)
        with self.assertRaises(RulePackParseError):
            self.loader.load(yaml_file)

    def test_loader_load_nonexistent_file(self) -> None:
        """Reject nonexistent file."""
        with self.assertRaises(RulePackParseError):
            self.loader.load(self.temp_path / "nonexistent.yaml")

    def test_loader_load_invalid_schema(self) -> None:
        """Reject invalid pack schema."""
        yaml_file = self.temp_path / "bad-schema.yaml"
        with open(yaml_file, "w") as f:
            yaml.safe_dump(
                {
                    "metadata": {
                        "pack_id": "PACK-TEST-001",
                        # Missing required version field
                    },
                    "rules": [],
                },
                f,
            )

        with self.assertRaises(RulePackValidationError):
            self.loader.load(yaml_file)

    def test_loader_load_empty_rules_list(self) -> None:
        """Valid to load pack with no rules."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-EMPTY-001",
                version="1.0.0",
            ),
            rules=[],
        )
        yaml_file = create_valid_yaml(self.temp_path, pack)
        loaded = self.loader.load(yaml_file)
        self.assertEqual(len(loaded.rules), 0)


# ============================================================================
# Test Cases: Archive Management
# ============================================================================


class TestArchiveManagement(unittest.TestCase):
    """Test rule pack archival and versioning."""

    def setUp(self) -> None:
        """Create temp directory and loader."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.factory = RuleFactory()
        self.loader = RulePackLoader(
            factory=self.factory,
            archive_dir=self.temp_path / "archive",
        )

    def tearDown(self) -> None:
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_archive_pack_version(self) -> None:
        """Archive rule pack version."""
        pack = create_valid_pack()
        archive_dir = self.temp_path / "archive"

        archive_path = self.loader.archive_version(pack, target_dir=archive_dir)

        self.assertTrue(archive_path.exists())
        self.assertIn("rule_pack-", archive_path.name)
        self.assertIn("1.0.0", archive_path.name)

    def test_archive_creates_directory_if_missing(self) -> None:
        """Archive operation creates missing directory."""
        pack = create_valid_pack()
        archive_dir = self.temp_path / "new_archive"

        self.assertFalse(archive_dir.exists())
        self.loader.archive_version(pack, target_dir=archive_dir)
        self.assertTrue(archive_dir.exists())

    def test_list_archived_versions(self) -> None:
        """List archived versions."""
        archive_dir = self.temp_path / "archive"
        pack1 = create_valid_pack()
        pack2 = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-TEST-001",
                version="1.1.0",
            ),
            rules=pack1.rules,
        )

        self.loader.archive_version(pack1, target_dir=archive_dir)
        self.loader.archive_version(pack2, target_dir=archive_dir)

        archives = self.loader.list_archived_versions(archive_dir=archive_dir)
        self.assertEqual(len(archives), 2)

    def test_archive_manager_cleanup_old_versions(self) -> None:
        """Archive manager cleans up old versions."""
        archive_dir = self.temp_path / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        manager = ArchiveManager(archive_dir)

        # Create test archive files
        for i in range(5):
            archive_file = archive_dir / f"rule_pack-1.0.{i}-20260817-100000.yaml"
            archive_file.write_text(f"version: 1.0.{i}")

        # Cleanup keeping only 2
        deleted = manager.cleanup_old_versions(keep_count=2)
        self.assertEqual(deleted, 3)
        self.assertEqual(len(list(archive_dir.glob("*.yaml"))), 2)


# ============================================================================
# Test Cases: Version Checking
# ============================================================================


class TestVersionChecking(unittest.TestCase):
    """Test rule pack version validation."""

    def setUp(self) -> None:
        """Create loader."""
        self.factory = RuleFactory()
        self.loader = RulePackLoader(factory=self.factory)

    def test_version_check_no_lock(self) -> None:
        """No warning when no locked version."""
        pack = create_valid_pack()
        result = self.loader.check_version(pack, locked_version=None)
        self.assertTrue(result)

    def test_version_check_new_equals_locked(self) -> None:
        """Pass when new == locked."""
        pack = create_valid_pack()  # v1.0.0
        result = self.loader.check_version(pack, locked_version="1.0.0")
        self.assertTrue(result)

    def test_version_check_new_greater_than_locked(self) -> None:
        """Pass when new > locked."""
        pack = create_valid_pack()  # v1.0.0
        result = self.loader.check_version(pack, locked_version="0.9.0")
        self.assertTrue(result)

    def test_version_check_new_less_than_locked(self) -> None:
        """Warning when new < locked."""
        pack = create_valid_pack()  # v1.0.0
        result = self.loader.check_version(pack, locked_version="2.0.0")
        self.assertFalse(result)

    def test_version_comparison_complex(self) -> None:
        """Complex version comparisons."""
        pack = RulePack(
            metadata=RulePackMetadata(
                pack_id="PACK-TEST-001",
                version="2.3.1",
            ),
            rules=[],
        )
        self.assertTrue(self.loader.check_version(pack, locked_version="2.3.0"))
        self.assertTrue(self.loader.check_version(pack, locked_version="2.2.9"))
        self.assertFalse(self.loader.check_version(pack, locked_version="2.3.2"))


# ============================================================================
# Test Cases: Integration
# ============================================================================


class TestIntegration(unittest.TestCase):
    """Integration tests for loader and archive."""

    def setUp(self) -> None:
        """Create temp directory and loader."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.factory = RuleFactory()
        self.loader = RulePackLoader(
            factory=self.factory,
            archive_dir=self.temp_path / "archive",
        )

    def tearDown(self) -> None:
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_end_to_end_load_and_archive(self) -> None:
        """End-to-end: load pack from YAML and archive it."""
        pack = create_valid_pack()
        yaml_file = create_valid_yaml(self.temp_path, pack)

        # Load
        loaded = self.loader.load(yaml_file)
        self.assertEqual(loaded.metadata.pack_id, "PACK-TEST-001")

        # Archive
        archive_path = self.loader.archive_version(
            loaded, target_dir=self.temp_path / "archive"
        )
        self.assertTrue(archive_path.exists())

    def test_load_parse_archive_with_version_check(self) -> None:
        """Load → parse → check version → archive."""
        pack = create_valid_pack()
        yaml_file = create_valid_yaml(self.temp_path, pack)

        loaded = self.loader.load(yaml_file)
        version_ok = self.loader.check_version(loaded, locked_version="0.9.0")
        self.assertTrue(version_ok)

        archive_path = self.loader.archive_version(
            loaded, target_dir=self.temp_path / "archive"
        )
        self.assertTrue(archive_path.exists())


if __name__ == "__main__":
    unittest.main()
