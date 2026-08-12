from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Mapping

BatchValidationStatus = Literal["accepted", "rejected", "quarantined", "partial-ingest"]

SUPPORTED_RESOURCE_TYPES = frozenset(
    {
        "Condition",
        "MedicationRequest",
        "Procedure",
        "Encounter",
        "Observation",
        "CarePlan",
    }
)


@dataclass(frozen=True)
class RecordValidationError:
    index: int
    reason: str
    resource_type: str | None = None
    record_id: str | None = None


@dataclass(frozen=True)
class BatchEnvelope:
    batch_id: str
    source: str
    records: List[Mapping[str, Any]]


@dataclass(frozen=True)
class BatchValidationResult:
    status: BatchValidationStatus
    accepted_records: List[Mapping[str, Any]] = field(default_factory=list)
    quarantined_records: List[Mapping[str, Any]] = field(default_factory=list)
    errors: List[RecordValidationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_accepted(self) -> bool:
        return self.status in {"accepted", "partial-ingest"}


def build_batch_envelope(payload: Mapping[str, Any]) -> BatchEnvelope:
    batch_id = payload.get("batch_id")
    source = payload.get("source")
    records = payload.get("records")

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    typed_records: List[Mapping[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each record must be an object")
        typed_records.append(record)

    return BatchEnvelope(batch_id=batch_id, source=source, records=typed_records)


def validate_batch_payload(payload: Mapping[str, Any]) -> BatchValidationResult:
    try:
        envelope = build_batch_envelope(payload)
    except ValueError as exc:
        return BatchValidationResult(
            status="rejected",
            errors=[RecordValidationError(index=-1, reason=str(exc))],
            metadata={"accepted_count": 0, "quarantined_count": 0, "total_count": 0},
        )

    if not envelope.records:
        return BatchValidationResult(
            status="rejected",
            errors=[RecordValidationError(index=-1, reason="records must not be empty")],
            metadata={
                "batch_id": envelope.batch_id,
                "source": envelope.source,
                "accepted_count": 0,
                "quarantined_count": 0,
                "total_count": 0,
            },
        )

    accepted_records: List[Mapping[str, Any]] = []
    quarantined_records: List[Mapping[str, Any]] = []
    errors: List[RecordValidationError] = []

    for index, record in enumerate(envelope.records):
        resource_type = record.get("resourceType")
        record_id = record.get("id")

        if not isinstance(resource_type, str) or not resource_type:
            quarantined_records.append(record)
            errors.append(
                RecordValidationError(index=index, reason="resourceType is required", record_id=str(record_id) if record_id else None)
            )
            continue

        if resource_type not in SUPPORTED_RESOURCE_TYPES:
            quarantined_records.append(record)
            errors.append(
                RecordValidationError(
                    index=index,
                    reason="unsupported resourceType",
                    resource_type=resource_type,
                    record_id=str(record_id) if record_id else None,
                )
            )
            continue

        if not isinstance(record_id, str) or not record_id:
            quarantined_records.append(record)
            errors.append(
                RecordValidationError(index=index, reason="id is required", resource_type=resource_type)
            )
            continue

        accepted_records.append(record)

    if accepted_records and quarantined_records:
        status: BatchValidationStatus = "partial-ingest"
    elif accepted_records:
        status = "accepted"
    else:
        status = "quarantined"

    return BatchValidationResult(
        status=status,
        accepted_records=accepted_records,
        quarantined_records=quarantined_records,
        errors=errors,
        metadata={
            "batch_id": envelope.batch_id,
            "source": envelope.source,
            "accepted_count": len(accepted_records),
            "quarantined_count": len(quarantined_records),
            "total_count": len(envelope.records),
        },
    )
