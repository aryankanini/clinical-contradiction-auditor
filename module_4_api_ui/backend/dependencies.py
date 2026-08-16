from __future__ import annotations

"""FastAPI dependency providers.

The object graph is wired in ``main.create_app`` and stashed on ``app.state``; these
providers only read it. That keeps business code free of global lookups, per the
dependency-injection rule in ``.propel/rules/python-architecture-standards.md``.
"""

from typing import Callable, Iterator

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from module_4_api_ui.backend.config import ApiConfig
from module_4_api_ui.backend.constants import Role
from module_4_api_ui.backend.errors import AuthenticationError, AuthorizationError
from module_4_api_ui.backend.security import Principal, is_known_role


def get_config(request: Request) -> ApiConfig:
	return request.app.state.config


def get_session_factory(request: Request) -> sessionmaker[Session]:
	return request.app.state.session_factory


def get_session(
	session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> Iterator[Session]:
	session = session_factory()
	try:
		yield session
	finally:
		session.close()


def get_audit_engine(request: Request):
	return request.app.state.audit_engine


def get_ai_orchestrator(request: Request):
	return request.app.state.ai_orchestrator


def get_job_registry(request: Request):
	return request.app.state.job_registry


def get_principal(
	x_user_id: str | None = Header(default=None, alias="X-User-Id"),
	x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> Principal:
	if not x_user_id or not x_user_id.strip():
		raise AuthenticationError(
			"X-User-Id header is required.",
			context={"header": "X-User-Id"},
		)
	if not x_user_role or not x_user_role.strip():
		raise AuthenticationError(
			"X-User-Role header is required.",
			context={"header": "X-User-Role"},
		)

	role = x_user_role.strip().lower()
	if not is_known_role(role):
		raise AuthorizationError(
			f"Unknown role '{role}'.",
			context={"allowed_roles": ["steward", "analyst", "compliance"]},
		)

	return Principal(user_id=x_user_id.strip(), role=role)  # type: ignore[arg-type]


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
	"""Build a dependency that rejects principals outside ``roles``.

	Routers use this as a first line of defence; services re-check authorization so the
	rule is enforced at the use-case layer too.
	"""

	allowed = frozenset(roles)

	def _guard(principal: Principal = Depends(get_principal)) -> Principal:
		if principal.role not in allowed:
			raise AuthorizationError(
				f"Role '{principal.role}' may not perform this action.",
				context={"required_roles": sorted(allowed), "actual_role": principal.role},
			)
		return principal

	return _guard
