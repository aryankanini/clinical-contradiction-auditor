# Troubleshooting Guide

## Migration Fails

Confirm PostgreSQL 14 or later is reachable through `DATABASE_URL`, then apply SQL migrations in numeric order. The migration role needs permission to create tables, indexes, functions, and triggers. Do not apply the PostgreSQL migrations to SQLite because JSONB, GIN indexes, and triggers are PostgreSQL features.

## Audit Update Or Delete Is Rejected

`audit_trail` is intentionally append-only. Record a compensating audit event instead of altering or removing a prior fact.

## Finding Is Rejected By The Safety Validator

Review the narrative and evidence strings against `data/safety_keywords.yaml`. Findings may describe contradictory data but must not give diagnosis, treatment, prescription, or recommendation language.

## Evidence Is Incomplete

Ensure raw rule output includes evidence items containing `field` and `value`, and that input resources have both `resourceType` and `id`. The evidence extractor reports 0% completeness when either field values or resource references are absent.

## Reproducibility Validation Fails

Verify that the same input snapshot, rule-pack version, timestamp context, and rule output were replayed. A changed resource, ordered list, or rule configuration produces a different SHA-256 output hash.