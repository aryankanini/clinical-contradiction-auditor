from __future__ import annotations

"""Rule packs and resolution queues.

Rule packs are read-only: publishing and activating versions is UC-004, which belongs to
the audit-engine module, not the API layer.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from module_4_api_ui.backend.dependencies import get_principal, get_session
from module_4_api_ui.backend.repositories import catalog_repository
from module_4_api_ui.backend.schemas.catalog import QueueOut, RulePackOut
from module_4_api_ui.backend.security import Principal
from shared.database.models import ResolutionQueueRow, RulePackRow


router = APIRouter(tags=["catalog"])


def _rule_pack_out(row: RulePackRow) -> RulePackOut:
	metadata = dict(row.metadata_json or {})
	rules = metadata.get("rules")
	return RulePackOut(
		id=row.id,
		version=row.version,
		status=row.status,
		published_at=row.published_at,
		metadata=metadata,
		rule_count=len(rules) if isinstance(rules, list) else 0,
		is_placeholder=bool(metadata.get("placeholder")),
	)


def _queue_out(row: ResolutionQueueRow, open_count: int) -> QueueOut:
	return QueueOut(
		id=row.id,
		name=row.name,
		owner_type=row.owner_type,
		config=dict(row.config_json or {}),
		open_count=open_count,
	)


@router.get("/rule-packs", response_model=List[RulePackOut])
def list_rule_packs(
	session: Session = Depends(get_session),
	principal: Principal = Depends(get_principal),
) -> List[RulePackOut]:
	return [_rule_pack_out(row) for row in catalog_repository.list_rule_packs(session)]


@router.get("/queues", response_model=List[QueueOut])
def list_queues(
	session: Session = Depends(get_session),
	principal: Principal = Depends(get_principal),
) -> List[QueueOut]:
	counts = catalog_repository.open_counts_by_queue(session)
	return [
		_queue_out(row, counts.get(row.id, 0)) for row in catalog_repository.list_queues(session)
	]
