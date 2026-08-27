from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class RulePackOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	version: str
	status: str
	published_at: datetime | None = None
	metadata: Dict[str, Any] = Field(default_factory=dict)
	rule_count: int = 0
	is_placeholder: bool = False


class QueueOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	name: str
	owner_type: str
	config: Dict[str, Any] = Field(default_factory=dict)
	open_count: int = 0


class AuditRunCreateRequest(BaseModel):
	batch_id: int
	rule_pack_version: str | None = None


class AuditRunOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	batch_id: int
	batch_external_id: str | None = None
	rule_pack_id: int
	rule_pack_version: str | None = None
	status: str
	started_at: datetime
	completed_at: datetime | None = None


