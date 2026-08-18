"""Rule pack schema and validation models using Pydantic.

Defines the structure for rule packs loaded from YAML files.
Pydantic v2.0+ validates schema, enforces constraints, and provides
error reporting for invalid rule pack definitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleDefinition(BaseModel):
    """Single rule definition within a rule pack.

    Attributes:
        rule_id: Unique identifier (e.g., "RULE-COND-001")
        version: Semantic version (e.g., "1.0.0")
        name: Human-readable rule name
        description: What the rule detects
        category: Rule category (diagnosis, medication, timeline, etc.)
        enabled: Whether rule is active in this pack
    """

    rule_id: str = Field(..., min_length=1, description="Unique rule identifier")
    version: str = Field(..., pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$", description="Semantic version")
    name: str = Field(..., min_length=1, description="Human-readable name")
    description: str = Field(..., min_length=1, description="Rule description")
    category: str = Field(..., min_length=1, description="Rule category")
    enabled: bool = Field(default=True, description="Whether rule is active")

    model_config = ConfigDict(
        frozen=True,  # Immutable
        json_schema_extra={
            "example": {
                "rule_id": "RULE-COND-001",
                "version": "1.0.0",
                "name": "Conflicting Condition Dates",
                "description": "Detects conditions with end_date before start_date",
                "category": "diagnosis",
                "enabled": True,
            }
        },
    )


class RulePackMetadata(BaseModel):
    """Metadata for a rule pack.

    Attributes:
        pack_id: Unique identifier for the pack (e.g., "PACK-001")
        version: Pack semantic version
        created_at: ISO 8601 timestamp
        description: Pack description
        author: Pack author/maintainer
        organization: Organization name
    """

    pack_id: str = Field(..., min_length=1, description="Unique pack identifier")
    version: str = Field(..., pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$", description="Semantic version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    description: str = Field(default="", description="Pack description")
    author: str = Field(default="", description="Pack author")
    organization: str = Field(default="", description="Organization")

    model_config = ConfigDict(
        frozen=True,  # Immutable
        json_schema_extra={
            "example": {
                "pack_id": "PACK-CLINICAL-001",
                "version": "1.0.0",
                "created_at": "2026-08-17T10:00:00",
                "description": "Clinical contradiction rules",
                "author": "Audit Team",
                "organization": "Clinical Engineering",
            }
        },
    )


class RulePack(BaseModel):
    """Complete rule pack with metadata and rules.

    Attributes:
        metadata: Pack metadata (id, version, timestamps)
        rules: List of rule definitions in this pack
    """

    metadata: RulePackMetadata = Field(..., description="Pack metadata")
    rules: List[RuleDefinition] = Field(default_factory=list, description="List of rules")

    model_config = ConfigDict(
        frozen=True,  # Immutable
        json_schema_extra={
            "example": {
                "metadata": {
                    "pack_id": "PACK-CLINICAL-001",
                    "version": "1.0.0",
                    "description": "Clinical contradiction rules",
                },
                "rules": [
                    {
                        "rule_id": "RULE-COND-001",
                        "version": "1.0.0",
                        "name": "Conflicting Condition Dates",
                        "description": "Detects conditions with end_date before start_date",
                        "category": "diagnosis",
                    }
                ],
            }
        },
    )

    @field_validator("rules")
    @classmethod
    def validate_unique_rule_ids(cls, rules: List[RuleDefinition]) -> List[RuleDefinition]:
        """Validate that all rule_ids are unique within the pack.

        Args:
            rules: List of rule definitions

        Returns:
            List of rules (if validation passes)

        Raises:
            ValueError: If duplicate rule_ids found
        """
        rule_ids = [rule.rule_id for rule in rules]
        if len(rule_ids) != len(set(rule_ids)):
            duplicates = [
                rid
                for rid in rule_ids
                if rule_ids.count(rid) > 1
            ]
            raise ValueError(
                f"Duplicate rule_ids in pack: {set(duplicates)}"
            )
        return rules

    @property
    def enabled_rules(self) -> List[RuleDefinition]:
        """Get only enabled rules from the pack.

        Returns:
            List of enabled rule definitions
        """
        return [rule for rule in self.rules if rule.enabled]

    @property
    def rule_id_to_definition(self) -> Dict[str, RuleDefinition]:
        """Create mapping of rule_id to rule definition.

        Returns:
            Dict mapping rule_id to RuleDefinition
        """
        return {rule.rule_id: rule for rule in self.rules}
