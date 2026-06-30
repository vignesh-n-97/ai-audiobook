# AUD-003 — FastAPI Service Bootstrap

**Epic:** EPIC 1 — Repository Foundation  
**Status:** ✅ Implemented  
**Priority:** Critical  
**Depends on:** AUD-002  
**Blocks:** AUD-020, AUD-010  

---

## Summary

Bootstraps the `api/` FastAPI application with structured JSON logging (structlog), OpenTelemetry tracing to Tempo, SQLAlchemy async DB session management, CORS middleware, and the initial router set.

---

## What Was Implemented

### Application Factory (`api/main.py`)

`create_app()` returns a configured `FastAPI` instance:
- Registers `LoggingMiddleware` (structlog JSON per-request logging)
- Registers `CORSMiddleware` (permissive in debug mode, locked down in production)
- Includes routers: `health`, `documents`, `experiments`
- Lifespan context: calls `init_db()` on startup, logs `api.started` with `git_sha`

### Health Check (`GET /health`)

File: `api/routers/health.py`

```json
{
  "status": "healthy",
  "db": "connected",
  "redis": "connected",
  "version": "<git-sha>"
}
```

- Executes `SELECT 1` against the async DB session to confirm connectivity
- Pings Redis via `redis.asyncio`
- Returns `git_sha` from `cfg.git_sha` (read from `GIT_SHA` env var)

### Structured Logging (`api/middleware/logging.py`)

Built on `structlog`. Every request emits a JSON log line containing:
- `method` — HTTP method
- `path` — request path
- `status_code` — response status
- `duration_ms` — request latency
- `request_id` — UUID generated per request

### OpenTelemetry Tracing (`api/middleware/tracing.py`)

Exports traces to Tempo via OTLP gRPC at `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `http://localhost:4317`). Service name is configurable via `OTEL_SERVICE_NAME`.

### DB Session (`api/db/session.py`)

- Async SQLAlchemy engine (`asyncpg` driver)
- `get_session()` FastAPI dependency yields `AsyncSession`
- `init_db()` called at lifespan startup to create tables

### DB Base (`api/db/base.py`)

Declarative `Base` with `__tablename__` from class name (snake_case).

### Config (`api/config.py`)

Re-exports `shared.Config`, adds API-specific fields (`api_host`, `api_port`, `api_debug`, `git_sha`). Uses `lru_cache` for singleton access via `get_config()`.

### Routers

| Router | Prefix | Status | Description |
|--------|--------|--------|-------------|
| `health.py` | `/health` | ✅ Implemented | DB + Redis connectivity check |
| `documents.py` | `/documents` | 🔲 Stub (AUD-020) | Document upload and management |
| `experiments.py` | `/experiments` | 🔲 Stub (AUD-010) | Experiment CRUD + run management |

---

## Files Changed

| File | Purpose |
|------|---------|
| `api/main.py` | Application factory + lifespan |
| `api/config.py` | API-specific config wrapper |
| `api/routers/health.py` | `GET /health` implementation |
| `api/routers/documents.py` | Stub router |
| `api/routers/experiments.py` | Stub router |
| `api/middleware/logging.py` | Structlog JSON middleware |
| `api/middleware/tracing.py` | OTEL tracing setup |
| `api/db/session.py` | Async session factory |
| `api/db/base.py` | Declarative Base |
| `shared/logging.py` | Shared `configure_logging()` helper |

---

## Running

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Acceptance Criteria Status

- [x] `GET /health` returns `200` with `{"status": "healthy"}`
- [x] Logs appear as JSON in stdout
- [x] Traces exported to Tempo via OTLP on startup
