from __future__ import annotations

from typing import Any, Dict, Generic, List, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from module_4_api_ui.backend.disclaimers import AUDIT_ONLY_NOTICE


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
	"""Envelope for every paginated collection."""

	items: List[T]
	total: int
	page: int
	page_size: int
	total_pages: int

	@classmethod
	def build(cls, items: Sequence[T], total: int, page: int, page_size: int) -> "Page[T]":
		total_pages = (total + page_size - 1) // page_size if page_size else 0
		return cls(
			items=list(items),
			total=total,
			page=page,
			page_size=page_size,
			total_pages=total_pages,
		)


class ErrorResponse(BaseModel):
	"""The single error envelope returned by every failing endpoint."""

	error: str = Field(description="Stable machine-readable error code.")
	detail: str
	context: Dict[str, Any] = Field(default_factory=dict)


class PrincipalOut(BaseModel):
	user_id: str
	role: str


class HealthOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	status: str
	database_reachable: bool
	audit_engine: str
	audit_engine_is_placeholder: bool
	ai_enabled: bool
	audit_only_notice: str = AUDIT_ONLY_NOTICE
