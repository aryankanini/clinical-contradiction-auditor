# API Contract — Module 4 (API + UI)

Service interface for the **AI-Powered Clinical Data Integrity Auditor**.

The BRD and spec define *what* the product must do (FR-001…FR-012, UC-001…UC-005) but
specify no endpoints, so this contract is derived from those requirements rather than
transcribed from them. It is the authoritative description of the HTTP surface; the live
OpenAPI schema at `/docs` is generated from the same code.

- **Base path:** `/api/v1`
- **Content type:** `application/json` (except `POST /batches/upload`, `multipart/form-data`)
- **Interactive docs:** `http://127.0.0.1:8000/docs`

## Audit-only boundary

Every response that can carry model-generated text also carries a fixed disclaimer
(FR-011). Deterministic rules establish findings; AI supplies explanation and confidence
context only and **never** changes a finding's status (FR-007). Two invariants are
enforced in code and asserted in tests:

- `POST /findings/{id}/explanation` does not modify `findings.status` or write to
  `finding_status_history`.
- A finding cannot enter `in_remediation` without both a human-approved resolution and an
  owner assignment (FR-009).

## Authentication and roles

No FR requires an identity system, so the API takes the caller's identity from headers
rather than a token. This is enough to satisfy FR-010's mixed-ownership routing and to
populate the `finding_status_history.changed_by` audit trail.

| Header | Required | Notes |
| --- | --- | --- |
| `X-User-Id` | yes | Recorded as `changed_by` / `approved_by` |
| `X-User-Role` | yes | One of `steward`, `analyst`, `compliance` (case-insensitive) |

`GET /health` is the only endpoint that needs neither. Missing headers → `401`; an
unrecognised role → `403`.

> **Not production authentication.** Any caller can assert any role. A deployment beyond
> pilot needs real identity in front of this.

## Error envelope

Every failure returns the same shape:

```json
{
  "error": "illegal_transition",
  "detail": "Cannot move a finding from 'new' to 'closed'.",
  "context": { "current_status": "new", "allowed": ["under_review", "non_actionable"] }
}
```

| Code | HTTP | Meaning |
| --- | --- | --- |
| `unauthenticated` | 401 | Identity headers missing |
| `forbidden` | 403 | Role not permitted |
| `not_found` | 404 | Resource does not exist |
| `conflict` | 409 | State conflict |
| `illegal_transition` | 409 | Status move not permitted by the state machine |
| `forbidden_transition` | 409 | Transition legal, but not for this role |
| `resolution_approval_required` | 409 | FR-009 gate: approval and assignment required |
| `transparency_incomplete` | 409 | UC-002 ext 2a: cannot accept a non-actionable finding |
| `no_published_rule_pack` | 409 | UC-001 ext 3a: run cannot be governed |
| `run_already_active` | 409 | A run is already in flight for the batch |
| `validation_error` | 422 | Domain validation failed |
| `request_validation_error` | 422 | Request body failed schema validation |
| `ai_draft_unavailable` | 422 | UC-003 ext 2a: no draft to approve |
| `ai_draft_low_confidence` | 422 | Draft must be edited or written manually |
| `upstream_unavailable` | 503 | AI provider unreachable or disabled |

## Endpoints

### Health and session

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | none | Reports DB reachability, engine in use, whether it is the placeholder |
| `GET` | `/session/me` | any | Echoes the resolved principal |

### Batches — UC-001, FR-001/FR-002

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `POST` | `/batches` | steward, analyst | Body `{batch_id, source, records[]}` |
| `POST` | `/batches/upload` | steward, analyst | `multipart/form-data`, field `file` |
| `GET` | `/batches` | any | Paginated; filter by `status`, `source` |
| `GET` | `/batches/{id}` | any | Counts, artifact paths, audit runs |
| `GET` | `/batches/{id}/resources` | any | Normalized resources + validation state |

Ingest status maps to HTTP: `accepted` → **201**, `partial-ingest` → **207** (with the
quarantine list in the body), `rejected`/`quarantined` → **422**.

### Audit runs — UC-001, FR-003/FR-004/FR-005/FR-008

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `POST` | `/audit-runs` | steward, analyst | **202**; executes in the background |
| `GET` | `/audit-runs` | any | Filter by `batch_id`, `status` |
| `GET` | `/audit-runs/{id}` | any | Status + severity/priority/outcome histograms |

Runs are queued and executed in a background task; the client polls
`GET /audit-runs/{id}` until `status` is `completed` or `failed`. Failure detail is
transient — `audit_runs` has no error column, so `error_message` comes from an
in-process registry and is lost on restart.

### Findings — UC-002, FR-006/FR-008

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `GET` | `/findings` | any | Prioritised queue (see filters below) |
| `GET` | `/findings/stats` | any | Counts by severity, status, priority, type |
| `GET` | `/findings/{id}` | any | Full transparency payload + allowed transitions |
| `GET` | `/findings/{id}/evidence` | any | Evidence joined to normalized resources |
| `GET` | `/findings/{id}/history` | any | Complete status trail |
| `POST` | `/findings/{id}/triage` | steward, analyst | `{disposition, notes}` |
| `POST` | `/findings/{id}/status` | steward, analyst, compliance | `{to_status, notes}` |

Filters on `GET /findings`: `audit_run_id`, `batch_id`, `status`, `severity`, `priority`,
`finding_type`, `rule_id`, `queue_id`, `open_only`, `search`, `page`, `page_size`. List
filters repeat (`?severity=critical&severity=high`). Default order is **priority, then
severity, then most recent** — the order a steward should work the queue in.

Triage dispositions map to statuses: `accept`→`accepted`, `defer`→`deferred`,
`escalate`→`escalated`, `dispute`→`disputed`. Triaging a finding still in `new` walks it
through `under_review` and writes a history row for each hop.

### AI explanations — FR-007, FR-011

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `POST` | `/findings/{id}/explanation` | steward, analyst | **200** if cached, **202** if generating |
| `GET` | `/findings/{id}/explanation` | any | Explanation, job status, or **204** |
| `GET` | `/findings/{id}/explanations` | any | All versions (FR-012) |

Generation calls module 3's `AIReasoningOrchestrator` (AWS Bedrock, three sequential
round-trips) in the background. `AI_ENABLED=false` makes these return `503`; evidence and
transparency review remain fully usable without AI.

**Degradation is explicit.** Module 3 parses model output by splitting on literal markers,
so a deviating response yields an empty `confidence_context`. That is surfaced as
`low_confidence: true` and counted as a missing transparency field rather than being
passed off as complete.

### Resolution and assignment — UC-003, FR-009/FR-010

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `GET` | `/findings/{id}/resolution/draft` | any | The model's proposal — advisory only |
| `GET` | `/findings/{id}/resolution` | any | Approved resolution, if any |
| `PUT` | `/findings/{id}/resolution` | steward | `{suggested_action, rationale, source, notes}` |
| `POST` | `/findings/{id}/assignment` | steward | `{queue_id?, assigned_to?}` |
| `GET` | `/queues` | any | Queues with open counts |
| `GET` | `/queues/{id}/findings` | any | Queue worklist |

`source` records provenance of the approved text: `ai`, `ai_edited`, or `manual`.
Assignment without a `queue_id` routes by each queue's `config_json.routing`; when nothing
matches, the finding goes to the governance queue and is escalated (UC-003 ext 4a).

### Rule packs — read-only

| Method | Path | Roles |
| --- | --- | --- |
| `GET` | `/rule-packs` | any |
| `GET` | `/rule-packs/{id}` | any |

Rule authoring, publishing, and activation (UC-004) belong to
`module_2_audit_engine` and are deliberately absent here.

### Compliance — UC-005, FR-006/FR-012

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| `POST` | `/compliance/samples` | compliance | Seeded, reproducible selection |
| `GET` | `/compliance/findings/{id}/reproducibility` | compliance | FR-012 check |
| `POST` | `/compliance/findings/{id}/verification` | compliance | Records sign-off |
| `POST` | `/compliance/exports` | compliance | Evidence bundle |

Sampling uses `random.Random(seed).sample(sorted(candidates), k)`, so the same criteria
always return the same findings — a reviewer can reproduce a colleague's sample without a
stored sample table.

Reproducibility reads the batch's **replay artifact** and confirms every evaluated record
can be reconstructed from it, satisfying the BRD's requirement to reproduce findings
"without re-running the full pipeline". A missing artifact yields
`reproducible: false` with the reason listed — never a 500 (UC-005 ext 2a).

## Finding status state machine (FR-010)

```
new ──→ under_review ──→ accepted ──→ in_remediation ──→ remediated ──→ closed
 │           │                              ↑
 │           ├──→ deferred ──→ under_review / closed_no_action
 │           ├──→ escalated ──────────────────┘
 │           ├──→ disputed ──→ under_review / accepted / closed_no_action
 └───────────┴──→ non_actionable ──→ under_review / closed_no_action
```

`closed` and `closed_no_action` are terminal. Which roles may move a finding *into* each
status:

| Target | Roles |
| --- | --- |
| `under_review`, `escalated`, `disputed`, `non_actionable`, `remediated` | steward, analyst |
| `accepted`, `deferred`, `in_remediation` | steward |
| `closed`, `closed_no_action` | steward, compliance |

`GET /findings/{id}` returns `allowed_transitions` already filtered for the caller's role
and preconditions, so a client need not reimplement these rules — but the server
re-validates every request regardless.

## Evidence type namespace

`finding_evidence` has no dedicated table for approved resolutions or compliance sign-off,
so `evidence_type` is namespaced. Engine-produced types carry a `normalized_resource_id`;
service-produced ones leave it `NULL` and are excluded from the evidence shown for a
finding.

| Type | Written by |
| --- | --- |
| `conflicting_record`, `governed_signal`, `rule_context` | Audit engine |
| `approved_resolution` | Resolution service |
| `compliance_verification` | Compliance service |

## Audit engine seam

> **`module_2_audit_engine` is not implemented yet.** Module 4 ships a placeholder,
> `StubAuditEngine`, so the API and UI are demoable in the meantime. Its rules are **not**
> authoritative clinical policy.

The contract module 2 must satisfy lives in
[module_4_api_ui/backend/audit_engine/port.py](../module_4_api_ui/backend/audit_engine/port.py):

```python
class AuditEnginePort(Protocol):
    @property
    def rule_pack_version(self) -> str: ...

    def evaluate_batch(
        self,
        resources: Sequence[Mapping[str, Any]],
        rule_pack: Mapping[str, Any],
    ) -> AuditEngineResult: ...
```

Module 2 does **not** import module 4. Result types come from
`shared/models/audit_finding.py`, and the input is a list of plain dicts in the shape
`ReplayArtifact.snapshots` already uses — the same shape module 3's `evidence_records`
consumes, so one record format flows ingest → engine → AI → API with no adapters.

Selection is controlled by `AUDIT_ENGINE`: `auto` (default) prefers module 2 and falls
back to the stub, `module_2` requires it, `stub` forces the placeholder. `/health` reports
which is live, and `RulePackOut.is_placeholder` surfaces it in the UI.

## Known limitations

- The header-based role model is a demonstration seam, not authentication.
- Background execution is in-process. Under multiple workers, `audit_runs.status` remains
  cross-process truth, but transient job error text and request dedupe are per-worker.
  Stranded `queued`/`running` runs are reconciled to `failed` at startup.
- `audit_runs` has no `error_message` column and `findings` has no `patient_id`, so run
  failure detail is transient and findings cannot be grouped by patient.
