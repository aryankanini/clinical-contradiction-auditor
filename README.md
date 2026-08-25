# AI-Powered Clinical Data Integrity Auditor

An **audit-only** system that detects cross-resource inconsistencies in FHIR patient
records — contradictions, stale states, timeline violations, and rule-expected
relationship gaps — before they become operational or risk-management failures.

Deterministic rules establish every finding. AI contributes explanation, evidence
synthesis, and confidence context *after* detection, and never changes a finding's status.
The system does not diagnose, prescribe, or alter clinical intent.

Source of truth: [`.propel/context/docs/brd.md`](.propel/context/docs/brd.md) and
[`.propel/context/docs/spec.md`](.propel/context/docs/spec.md).

## Modules

| Module | Responsibility | Status |
| --- | --- | --- |
| `module_1_data` | FHIR batch ingestion, normalization, validation, replay artifacts | Implemented |
| `module_2_audit_engine` | Deterministic contradiction detection and severity assignment | Implemented |
| `module_3_ai_reasoning` | Explanation, evidence synthesis, resolution drafts (AWS Bedrock) | Implemented |
| `module_4_api_ui` | Service interface and operator UI | Implemented |
| `shared` | Cross-module domain models, enums, database schema | Implemented |

## Setup

Requires Python 3.12+ (developed on 3.14) and Node 20+. **Run everything from the
repository root** — there is no `pyproject.toml`, so imports only resolve from there.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust as needed. The defaults target Postgres, but the
whole schema also runs on SQLite (`shared/database/models.py` declares
`JSON().with_variant(JSONB, "postgresql")`), so no database server is required for
development.

## Running

```powershell
# Start backend + frontend together (AI enabled by default)
.\scripts\start-app.ps1 -SkipSeed

# Optional: first run with reseed
.\scripts\start-app.ps1

# Optional: run with AI disabled
.\scripts\start-app.ps1 -SkipSeed -DisableAI

# Stop both services
.\scripts\stop-app.ps1
```

- API: <http://127.0.0.1:18080> · interactive docs at `/docs`
- UI: <http://localhost:5173> (proxies `/api` to the backend, so CORS never applies in dev)

Default dev startup enables AI explanation generation (`AI_ENABLED=true`). Use
`-DisableAI` when running without AWS credentials. Findings, evidence, triage, and
compliance export remain usable either way.

### Ingesting a batch from the CLI

```bash
python -m module_1_data.cli data/samples/demo_batch.json --pretty
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

Tests use the standard library's `unittest` against a temp-file SQLite database. No
Postgres, no AWS credentials, and no mocking library are needed — module 3 takes its
provider by constructor injection, so a fake is supplied directly.

## Architecture notes

Requests flow `routers → services → repositories → SQLAlchemy`, matching the layer model
in [`.propel/rules/python-architecture-standards.md`](.propel/rules/python-architecture-standards.md).
The object graph is wired at the composition root in `module_4_api_ui/backend/main.py`.

**Sync vs async.** SQLAlchemy here is synchronous and `ingest_batch()` blocks, so most
routes are declared `def` and FastAPI runs them in its worker threadpool. Only the AI
endpoints are `async def`, because module 3's orchestrator is genuinely awaitable.
Declaring the blocking routes `async` would stall the event loop.

**The audit engine seam.** Module 4 consumes the engine through `AuditEnginePort`
(a Protocol). `module_2_audit_engine.ContradictionDetector` now satisfies this
contract, and `/health` reports which engine is active. See
[`docs/api-contract.md`](docs/api-contract.md) for the full contract.

## Documentation

- [`docs/api-contract.md`](docs/api-contract.md) — endpoints, schemas, roles, state machine
- [`.propel/context/docs/brd.md`](.propel/context/docs/brd.md) — business requirements
- [`.propel/context/docs/spec.md`](.propel/context/docs/spec.md) — FR-001…FR-012, UC-001…UC-005
