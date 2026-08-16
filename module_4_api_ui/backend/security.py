from __future__ import annotations

"""Role model for the API.

The spec names three actors but states no authentication requirement, so identity
arrives as ``X-User-Id`` / ``X-User-Role`` headers rather than a token. That is enough
to satisfy FR-010's mixed-ownership routing and to populate the
``finding_status_history.changed_by`` audit trail, without inventing an identity system
no requirement asks for.
"""

from dataclasses import dataclass
from typing import FrozenSet

from module_4_api_ui.backend.constants import ROLES, Role


ROLE_STEWARD: Role = "steward"
ROLE_ANALYST: Role = "analyst"
ROLE_COMPLIANCE: Role = "compliance"


@dataclass(frozen=True)
class Principal:
	"""The caller, as asserted by request headers."""

	user_id: str
	role: Role

	def has_any_role(self, roles: FrozenSet[str]) -> bool:
		return self.role in roles


def is_known_role(value: str) -> bool:
	return value in ROLES
