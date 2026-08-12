from __future__ import annotations

from enum import Enum


class NormalizationState(str, Enum):
	VALID = "valid"
	MISSING = "missing"
	INVALID = "invalid"
	AMBIGUOUS = "ambiguous"
	UNRESOLVED = "unresolved"
	DERIVED = "derived"
