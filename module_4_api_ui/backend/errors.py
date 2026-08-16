from __future__ import annotations

"""Typed API exception hierarchy and the single error envelope.

The repository had no exception hierarchy before module 4; domain errors either
propagated raw or were folded into result objects. Everything raised here maps to a
consistent ``{"error": ..., "detail": ..., "context": {...}}`` body via the handlers
registered in ``main.create_app``.
"""

from typing import Any, Dict


class ApiError(Exception):
	"""Base class for every error the API deliberately returns."""

	status_code: int = 500
	code: str = "internal_error"

	def __init__(
		self,
		detail: str,
		*,
		code: str | None = None,
		status_code: int | None = None,
		context: Dict[str, Any] | None = None,
	) -> None:
		super().__init__(detail)
		self.detail = detail
		if code is not None:
			self.code = code
		if status_code is not None:
			self.status_code = status_code
		self.context: Dict[str, Any] = context or {}

	def to_payload(self) -> Dict[str, Any]:
		return {"error": self.code, "detail": self.detail, "context": self.context}


class NotFoundError(ApiError):
	status_code = 404
	code = "not_found"


class ValidationError(ApiError):
	status_code = 422
	code = "validation_error"


class ConflictError(ApiError):
	status_code = 409
	code = "conflict"


class AuthenticationError(ApiError):
	status_code = 401
	code = "unauthenticated"


class AuthorizationError(ApiError):
	status_code = 403
	code = "forbidden"


class IllegalTransitionError(ConflictError):
	code = "illegal_transition"


class AuditOnlyViolationError(ApiError):
	"""Raised when generated text would breach the FR-011 audit-only boundary."""

	status_code = 422
	code = "audit_only_violation"


class UpstreamUnavailableError(ApiError):
	"""The AI provider or another external dependency could not be reached."""

	status_code = 503
	code = "upstream_unavailable"
