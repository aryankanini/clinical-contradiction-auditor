from __future__ import annotations

from typing import Dict, List


GOVERNED_RELATIONSHIP_RULES: Dict[str, List[str]] = {
	"Condition": ["encounter"],
	"MedicationRequest": ["subject"],
	"Procedure": ["subject"],
	"Encounter": [],
	"Observation": [],
	"CarePlan": ["subject"],
}


def expected_relationships_for(resource_type: str) -> List[str]:
	return GOVERNED_RELATIONSHIP_RULES.get(resource_type, [])

