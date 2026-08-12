# Codebase Analysis

## Executive Summary

The repository currently captures product intent well but does not yet implement the product. The target architecture is clearly described in [.propel/context/docs/brd.md](.propel/context/docs/brd.md) and [.propel/context/docs/spec.md](.propel/context/docs/spec.md): batch FHIR ingestion, deterministic contradiction detection, AI-backed explanation, and an API/UI layer. In contrast, every tracked product file under `module_1_data`, `module_2_audit_engine`, `module_3_ai_reasoning`, `module_4_api_ui`, `shared`, `tests`, `docs`, `requirements.txt`, `docker-compose.yml`, and the frontend `package.json` is currently zero bytes.

This means the project is at a scaffold stage rather than an implementation stage. Architecture, security posture, performance behavior, data model, and integration topology can only be assessed as design intent plus delivery gaps. The only concrete runtime risk visible today is secret handling in the local environment configuration.

## Scope and Evidence

This analysis is based on:

- Intended product behavior in [.propel/context/docs/brd.md](.propel/context/docs/brd.md) and [.propel/context/docs/spec.md](.propel/context/docs/spec.md)
- Tracked repository structure from `git ls-files`
- File population checks across `module_1_data`, `module_2_audit_engine`, `module_3_ai_reasoning`, `module_4_api_ui`, `shared`, `tests`, `docs`, and `data`
- Diagnostics scan across product directories
- Environment and repository hygiene review of `.env`, `.env.example`, and `.gitignore`

## Current State Snapshot

| Area | Files | Non-empty files | Assessment |
| --- | ---: | ---: | --- |
| `module_1_data` | 4 | 0 | No ingestion implementation |
| `module_2_audit_engine` | 7 | 0 | No rule engine or severity logic |
| `module_3_ai_reasoning` | 8 | 0 | No orchestration, prompts, or provider integration |
| `module_4_api_ui` | 2 | 0 | No backend API or frontend application |
| `shared` | 3 | 0 | No shared models or enums |
| `tests` | 4 | 0 | No unit or integration coverage |
| `docs` | 4 | 0 | No product-facing technical docs outside Propel artifacts |
| `data` | 4 | 0 | No sample, raw, or processed datasets |

Additional observations:

- `requirements.txt` is empty
- `docker-compose.yml` is empty
- `module_4_api_ui/frontend/package.json` is empty
- No GitHub Actions workflows were found under `.github/workflows`
- Product directories report no editor diagnostics because the code is not yet present

## Architecture Assessment

### Intended architecture

The repository structure and specification define a sensible modular split:

- `module_1_data`: FHIR batch ingestion and normalization
- `module_2_audit_engine`: deterministic contradiction detection and severity assignment
- `module_3_ai_reasoning`: explanation, evidence synthesis, and human-reviewed resolution drafts
- `module_4_api_ui`: service interface and operator UI
- `shared`: common domain models and enums

This decomposition is appropriate for the stated safety model because it separates deterministic adjudication from AI-generated explanation.

### Actual architecture state

There is no executable architecture yet. The current repo demonstrates naming, boundaries, and artifact flow, but not control flow, interfaces, contracts, or deployment packaging. That creates three immediate consequences:

- No way to verify that the deterministic engine is truly authoritative at runtime
- No way to verify that AI is prevented from mutating findings or crossing the audit-only boundary
- No way to validate module contracts, failure modes, or cross-layer observability

### Architectural risk

The main architectural risk is not wrong structure; it is missing structure in code. If implementation begins without first codifying shared finding models, rule interfaces, and service boundaries, the deterministic-first safety principle in the spec will be easy to erode.

## Security Assessment

### Positive design signals

- The BRD and spec consistently enforce an audit-only boundary and explicitly prohibit diagnosis, treatment advice, or clinical intent alteration.
- The planned deterministic-first design is a strong safety control if implemented faithfully.

### Current security gaps

- A real-looking API key is present in the local `.env` file. `.gitignore` includes `.env`, which is correct, but secret presence in the workspace still creates exposure risk if the file was ever copied, shared, or committed outside ignore protection.
- There is no application code implementing authentication, authorization, request validation, structured logging, audit access controls, or secrets loading.
- There are no pinned Python or frontend dependencies yet, so no supply-chain posture exists.
- There is no container, infrastructure, or CI policy enforcement in the product runtime paths.

### Security conclusion

The current codebase is safer by omission than by control. The product cannot yet be attacked through its app surfaces because those surfaces do not exist, but it also has none of the security controls required for a healthcare-adjacent audit system.

## Performance Assessment

### What can be measured now

There is no runtime to benchmark. No ingestion pipeline, rule execution path, API path, or AI call path exists.

### Performance risks implied by the design

- Cross-resource contradiction detection can become quadratic if patient resources are repeatedly scanned without indexed joins or normalized lookup maps.
- Batch-oriented FHIR ingestion can become memory-heavy if full cohorts are loaded before normalization and rule execution.
- AI rationale generation can dominate latency and cost if invoked synchronously for every finding instead of only for triaged findings or batched evidence packets.
- Missing sample data and benchmarks mean there is no path yet to validate the pilot goals in the spec.

### Performance conclusion

Performance risk is currently architectural, not operational. The project should establish benchmark datasets, rule-engine complexity targets, and AI invocation budgets before large-scale implementation begins.

## Data Model Assessment

### Intended model

The spec names the core resource types: Conditions, Medications, Procedures, Encounters, Observations, and CarePlans. It also requires normalized status, timestamps, reference linkage, rule IDs, evidence references, timestamps, audit outcomes, severity, and AI confidence context.

### Actual model state

- No domain models exist under `shared/models`
- No enums exist under `shared/enums`
- No FHIR parsing or normalization logic exists under `module_1_data/ingestion`
- No contradiction finding schema exists for deterministic and AI outputs
- No rule catalog exists in the tracked `module_2_audit_engine/rules` files

### Data-model conclusion

The codebase has a strong conceptual model but no canonical schema. This is the most important technical gap to close before implementing the audit engine because every downstream layer depends on stable resource and finding contracts.

## Integration Topology Assessment

### Intended integrations

The documented topology implies these external dependencies:

- FHIR or EHR source systems for resource bundles
- A rule management source for versioned deterministic rules
- An LLM provider for explanation and resolution drafting
- A backend API consumed by triage and compliance users

### Actual integrations

No integration code exists for:

- FHIR ingestion
- Rule-pack loading or versioning
- LLM provider configuration or invocation
- API routing, serialization, or UI transport

### Integration conclusion

Integration topology is fully conceptual today. The most important near-term decision is to define stable boundaries between ingestion, deterministic findings, explanation generation, and operator workflows before any vendor-specific integration is added.

## Testing and Delivery Assessment

- No unit tests, integration tests, or sample cases are implemented
- No build or test commands are defined in package or dependency manifests
- No CI workflows are present under `.github/workflows`
- No deployable application packaging exists for backend or frontend
- No data fixtures exist to prove contradiction detection, severity scoring, or safety-bound behavior

This is a delivery-readiness gap, not just a quality gap. There is nothing yet that can be executed in CI, deployed to an environment, or validated against the pilot metrics in the spec.

## Key Findings

### Critical

1. The product codebase is structurally present but functionally unimplemented. All tracked files in the core application, tests, product docs, and runtime manifests are empty.

### High

1. The repository has no canonical shared data model for FHIR normalization or contradiction findings, which blocks safe implementation of every downstream module.
2. There is no test harness, benchmark dataset, or CI workflow, so none of the safety, accuracy, or performance claims in the spec can be validated.
3. A real secret is present in the local `.env` file. If it has ever been committed or shared outside the ignored local workspace, it should be rotated.

### Medium

1. The intended separation between deterministic adjudication and AI explanation exists only in documentation, not in enforceable interfaces.
2. Dependency and deployment manifests are empty, so the supply-chain and runtime posture is undefined.
3. Product-facing technical docs under `docs/` are empty, leaving implementation guidance trapped in Propel artifacts only.

## Prioritized Recommendations

### Phase 0: Hygiene and safety baseline

1. Rotate the live secret from `.env` if there is any chance it left the local machine or entered git history.
2. Replace `.env` usage with a documented local-only secret loading pattern and keep `.env.example` as placeholders only.
3. Add minimal dependency manifests for backend and frontend so the runtime surface is explicit.

### Phase 1: Define canonical contracts

1. Implement shared domain models for normalized FHIR resources, contradiction findings, evidence packets, severity, and workflow state.
2. Define the deterministic rule engine interface before writing individual rules.
3. Define a hard contract that AI receives immutable deterministic findings and can only append explanation-oriented fields.

### Phase 2: Build the deterministic backbone first

1. Implement FHIR ingestion and normalization for the six in-scope resource types.
2. Implement a small rule pack that proves the deterministic-first architecture end to end.
3. Add reproducible audit-log artifacts as part of the first working pipeline, not as a later enhancement.

### Phase 3: Add AI and operator surfaces second

1. Implement the AI provider behind a narrow interface that cannot alter contradiction status.
2. Generate rationale only from deterministic findings and evidence payloads.
3. Expose findings through a minimal backend API before building a broader frontend experience.

### Phase 4: Prove quality gates

1. Add unit tests for normalization, rule evaluation, severity assignment, and boundary enforcement.
2. Add integration tests with labeled sample cases for contradiction truth sets.
3. Add CI checks for tests, linting, secret scanning, and dependency validation.

## Overall Assessment

The project has strong problem framing and a reasonable intended architecture, but it is still a design artifact repository rather than an application codebase. The next successful move is not broad implementation across all modules; it is establishing canonical models, deterministic interfaces, and a thin executable vertical slice that proves the audit-only architecture in code.
