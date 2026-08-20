# Codebase Analysis

## Executive Summary

The repository has progressed from scaffolding to a runnable, database-backed audit workflow. It implements FHIR-style batch ingestion, normalized-resource persistence, a FastAPI service, an operator UI, AI explanation orchestration, resolution workflows, and compliance exports. The latest Module 2 changes add real deterministic rule classes and execution infrastructure, but the current full unit/API discovery run is failing because existing API rule-pack creation paths do not populate the newly required `rule_packs.rule_pack_id` field.

The most important near-term task is therefore compatibility repair: align rule-pack seed/test/repository creation with the expanded Module 2 schema, restore green tests, then implement `ContradictionDetector` as the adapter that makes Module 2 authoritative through the existing API audit-engine port.

## Scope and Evidence

This analysis is based on:

- Functional requirements and use cases in [.propel/context/docs/spec.md](.propel/context/docs/spec.md)
- Product boundaries in [.propel/context/docs/brd.md](.propel/context/docs/brd.md)
- Current checkout after the latest Module 2 rule changes
- Full unit/API discovery that exposed `NOT NULL constraint failed: rule_packs.rule_pack_id` in API audit-run setup
- Frontend production build completion
- Source inspection of Modules 1 through 4, shared persistence, and runtime configuration

## Current State Snapshot

| Area | Current State | Assessment |
| --- | --- | --- |
| Module 1 data | Batch intake, normalization, validation, replay/provenance artifacts, optional relational writes | Implemented |
| Module 2 audit engine | Rule interface, execution orchestration, rule-pack schema, and timeline rules exist; `ContradictionDetector` remains empty | Partially implemented |
| Module 3 AI reasoning | Bedrock provider, orchestrator, agents, prompts, failure handling | Implemented; external credentials required for live use |
| Module 4 API | FastAPI routes, workflow services, repositories, health, compliance export | Implemented |
| Module 4 UI | React/Vite operator application with findings, batch, dashboard, and detail views | Implemented and builds |
| Shared database | SQLAlchemy model, session, and configuration layer | Implemented |
| Tests | Unit and API coverage for ingestion, audit workflow, AI failure paths, compliance, and resolution | Regression currently blocks API audit-run test setup |
| CI/CD | No GitHub Actions workflow found | Not implemented |

## Architecture Assessment

### Implemented Architecture

The application follows a practical layered structure:

- Module 1 turns batch payloads into normalized, validated resources and persisted artifact metadata.
- Module 4 receives workflow requests, uses repositories for persistence, and delegates rule evaluation through `AuditEnginePort`.
- Module 3 is isolated behind an orchestrator/provider boundary and returns explanations without changing finding status.
- The React operator UI communicates with the versioned API under `/api/v1`.
- Shared SQLAlchemy models provide persistence boundaries for batches, normalized resources, findings, evidence, workflow status, queues, and AI explanation records.

The composition root in [main.py](module_4_api_ui/backend/main.py) supports dependency injection for session factories, audit engines, and AI orchestrators. This enables isolated temp-file SQLite API tests without patching global state.

### Architectural Strengths

- The audit-only boundary is explicit in service description, outcome handling, and AI explanation behavior.
- The API has a defined engine seam through `AuditEnginePort`.
- Database schema supports normalized data, governance signals, workflow state, evidence, audit runs, and AI explanation records.
- The project uses JSON with a PostgreSQL JSONB variant, making SQLite usable for local tests while keeping PostgreSQL viable for deployment.

### Architectural Gaps

- Module 4's `StubAuditEngine` still owns the rules used by the live API because Module 2 has no `ContradictionDetector` adapter implementing `AuditEnginePort`.
- The expanded `RulePackRow` schema requires `rule_pack_id`, but existing API tests and seed paths create rule packs with only `version`. This breaks SQLite API setup before audit-run behavior is exercised.
- `create_all` is used to create tables at runtime. Alembic migrations are declared as a dependency but not yet configured as the schema lifecycle mechanism.
- The old source-of-truth artifacts still present an ingestion-only implementation view and do not capture the API, UI, AI, and workflow delivery now on main.

## Security Assessment

### Current Controls

- API request validation uses FastAPI/Pydantic schemas.
- Authorization checks use named roles for steward, analyst, and compliance workflows.
- The AI service can be disabled with `AI_ENABLED=false` so audit workflows remain usable without external AI credentials.
- The application records explicit safety metadata and distinguishes non-actionable findings from confirmed outcomes.

### Gaps and Risks

1. Identity is currently asserted through `X-User-Id` and `X-User-Role` request headers. This is appropriate for local testing but not trusted authentication for a deployed system.
2. The local `.env` file contains an API key and must remain ignored. Rotate it if it was exposed outside the local environment.
3. The application uses synchronous SQLAlchemy and file artifacts; production storage access, encryption, retention, backup, and authorization policy are not yet specified.
4. Live Bedrock use depends on AWS credentials and runtime permissions, which are not validated by local tests.

## Performance Assessment

### Current Behavior

- Ingestion and repository operations are synchronous and are executed through FastAPI's worker-thread handling for synchronous routes.
- Module 2's execution plan and rule orchestration are designed for canonical ordering and reproducibility; the API still executes the Module 4 placeholder engine.
- The default batch ceiling is configurable through `API_MAX_BATCH_RECORDS`, with a default of `5000`.

### Risks

- Batch normalization, rule evaluation, and artifact generation are in-process and do not yet have queue-based execution or horizontal worker scaling.
- File-backed replay/provenance artifacts are appropriate for local workflows but need object storage and retention controls for production scale.
- There are no performance benchmarks for the pilot thresholds, large FHIR cohorts, or concurrent audit runs.

## Data Model Assessment

The data model is materially implemented and aligns well with the required workflow:

- `ingest_batches`, `ingest_records`, and `normalized_resources` preserve batch and normalized FHIR context.
- `validation_states` and `governed_relationship_signals` preserve incompleteness and rule-governed relationship gaps.
- `rule_packs`, `audit_runs`, `findings`, and `finding_evidence` support deterministic rule traceability.
- `resolution_queues`, `finding_assignments`, and `finding_status_history` support governed workflow routing and closure.
- `ai_explanations` persists supplemental AI output separately from deterministic findings.

Remaining data-model work is operational rather than conceptual: introduce migration management, define artifact retention policies, and validate PostgreSQL indexes using representative pilot data.

## Integration Topology Assessment

### Implemented Integrations

- FHIR-like batch input through the ingestion/API batch workflow
- PostgreSQL-compatible SQLAlchemy persistence with SQLite test compatibility
- React/Vite frontend calling FastAPI endpoints
- Optional AWS Bedrock provider for explanation generation
- File-backed provenance, replay, and compliance export artifacts

### Pending Integrations

- Real EHR/FHIR source authentication and transport
- Production PostgreSQL deployment and migration lifecycle
- Real identity provider for API users
- AWS credential, observability, and cost governance for Bedrock
- Object storage for durable artifacts

## Testing and Delivery Assessment

- The previous main-branch baseline passed 167 unit/API tests and the frontend build completed successfully.
- The latest full discovery run fails during API audit-run setup because `rule_packs.rule_pack_id` is non-nullable and not populated by older construction paths.
- API tests use a temp-file SQLite database and dependency injection, providing strong local workflow confidence once the compatibility regression is repaired.
- Error behavior for AI throttling/failure is covered by test output.

Delivery gaps:

- No CI workflow is present to run backend tests, frontend build/typecheck, or schema validation on pull requests.
- No persistent PostgreSQL integration test is present.
- No browser-level end-to-end test suite is present for the operator UI.

## Key Findings

### High

1. The latest Module 2 schema change breaks API audit-run tests because `RulePackRow.rule_pack_id` is required but not supplied by existing test and seed creation paths. Make the new identity field backward-compatible or update all construction paths, then restore the full test suite.

2. The app currently uses Module 4's `StubAuditEngine` as the deterministic rule owner because `module_2_audit_engine.ContradictionDetector` is empty. Implement the real Module 2 engine behind the existing port before treating findings as authoritative.

3. Header-derived roles are not production authentication. Replace them with a trusted identity integration before exposing the API beyond local or controlled development environments.

### Medium

1. Replace runtime `create_all` with Alembic migrations before persistent PostgreSQL deployment.

2. Add CI gates for Python tests, frontend typecheck/build, secret scanning, and migration verification.

3. Refresh epics, user stories, task artifacts, and the implementation analysis to represent the merged Module 3 and Module 4 scope.

4. Add production artifact retention, access controls, encryption, and backup policy for replay/provenance/compliance outputs.

### Low

1. Add performance baselines for batch volume, audit-run latency, and concurrent workloads.

2. Add browser-level UI journeys after the API workflow is stable against a real database.

## Prioritized Next Approach

1. Repair the `RulePackRow.rule_pack_id` compatibility regression in seed, repository, and test construction paths; rerun full discovery until green.

2. Implement `module_2_audit_engine.ContradictionDetector` so it fulfills the existing `AuditEnginePort`, then run API tests with `AUDIT_ENGINE=module_2`.

3. Add Alembic configuration and an initial migration from the current SQLAlchemy metadata.

4. Establish CI for backend tests, frontend build/typecheck, and migration smoke checks.

5. Add a production identity solution and remove trust in caller-provided role headers.

6. Refresh the project planning artifacts to make Module 2 ownership and production hardening visible in the delivery backlog.

## Overall Assessment

The application is now a demoable audit workflow rather than a scaffold. Its central architectural seam is healthy: ingestion, persistence, API/UI, and AI explanation are already decoupled from the rule engine. The current priority is to stabilize the evolving Module 2 schema and complete the authoritative engine adapter before resuming production hardening.
