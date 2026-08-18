# Deployment Guide

## Prerequisites

Use Python 3.10 or later, PostgreSQL 14 or later, and the dependencies in `requirements.txt`.

## Setup

Set `DATABASE_URL` to a PostgreSQL connection string. Apply the ordered SQL files in `shared/database/migrations/` using a database role permitted to create tables, indexes, and triggers. The application role should have only the required read/write permissions and must not bypass audit protections.

## Verification

Run `python -m pytest tests/unit tests/integration -q`. Verify that `audit_trail` rejects update and delete attempts, then run a reproducibility audit after an execution batch.

## Operations

Keep rule packs and safety-keyword configuration under source control. Monitor execution duration, rejected safety findings, and reproducibility validation rate. Investigate any rate below 95% before relying on an audit batch.