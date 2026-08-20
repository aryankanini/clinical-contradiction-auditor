# Running the Clinical Contradiction Auditor

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |

All commands must be run from the **repository root** unless stated otherwise.

---

## First-Time Setup

### 1. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
copy .env.example .env
```

Open `.env` and adjust if needed. The defaults work out of the box for local SQLite development.

### 3. Seed the database

This creates the SQLite dev database, populates demo rule packs, queues, batches, and findings:

```powershell
python -m module_4_api_ui.backend.seed --database-url "sqlite+pysqlite:///./dev.db" --reset
```

Expected output — 3 batches and 11 findings seeded:

```json
{
  "rule_pack_version": "stub-2026.08.1",
  "queues": 4,
  "batches": [
    { "batch_id": "demo-contradiction",     "status": "accepted",       "findings": 4 },
    { "batch_id": "demo-stale-timeline",    "status": "accepted",       "findings": 4 },
    { "batch_id": "demo-relationship-gaps", "status": "partial-ingest", "findings": 3 }
  ]
}
```

> Re-run with `--reset` any time you want a clean slate.

### 4. Install frontend dependencies

```powershell
cd module_4_api_ui\frontend
npm install
cd ..\..
```

---

## Running

Open **two separate terminals**, both from the repository root.

### Terminal 1 — Backend (FastAPI)

```powershell
$env:DATABASE_URL = "sqlite+pysqlite:///./dev.db"
$env:AI_ENABLED   = "false"
python -m uvicorn module_4_api_ui.backend.main:app --reload
```

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/docs` | Swagger UI — interactive API explorer |
| `http://127.0.0.1:8000/redoc` | ReDoc — alternative API docs |
| `http://127.0.0.1:8000/api/v1/health` | Health check endpoint |

> `AI_ENABLED=false` lets the API run without AWS credentials.
> All findings, evidence, triage, and compliance export remain fully usable.
> Only AI rationale generation is skipped.

### Terminal 2 — Frontend (React + Vite)

```powershell
cd module_4_api_ui\frontend
npm run dev
```

| URL | Description |
|---|---|
| `http://localhost:5173` | Main UI |

The frontend proxies all `/api` requests to the backend automatically — no CORS issues in development.

---

## Using the Swagger UI

The API requires two headers on every request. Set them once in Swagger using the **Authorize** button (top right):

| Header | Value |
|---|---|
| `X-User-Id` | `demo-steward` |
| `X-User-Role` | `steward` |

Available roles: `steward`, `analyst`, `compliance`

---

## Enabling AI Reasoning (AWS Bedrock)

To enable AI-generated explanations, set these before starting the backend:

```powershell
$env:AI_ENABLED        = "true"
$env:AWS_REGION        = "us-east-1"
$env:BEDROCK_MODEL_ID  = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

AWS credentials must be configured (`aws configure` or an active IAM role).
The Bedrock client is lazy — missing credentials surface as a failed explanation job, not a dead server.

---

## Project URLs Summary

| Service | URL |
|---|---|
| Frontend UI | `http://localhost:5173` |
| Backend API | `http://127.0.0.1:8000` |
| Swagger docs | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |
| Health check | `http://127.0.0.1:8000/api/v1/health` |

---

## Known Issues

- **`AI_ENABLED=true` without AWS credentials** — the server boots fine but explanation jobs will fail with a credential error. Set `AI_ENABLED=false` for local development without Bedrock access.
- **Re-seeding without `--reset`** — running the seed a second time without `--reset` will skip already-existing rule packs and queues but may duplicate batches. Always use `--reset` for a clean environment.
- **Port conflicts** — if port `8000` or `5173` is already in use, stop the conflicting process or change the port with `--port XXXX` (uvicorn) or `--port XXXX` (vite).
