# AUD-002 — Docker Development Environment

**Epic:** EPIC 1 — Repository Foundation  
**Status:** ✅ Implemented  
**Priority:** Critical  
**Depends on:** AUD-001  
**Blocks:** AUD-003, AUD-010  

---

## Summary

Defines the `docker-compose.yml` at the repo root, bringing up all infrastructure services required for local development: database, message broker, experiment tracking, LLM observability, and the full observability stack.

---

## What Was Implemented

### `docker-compose.yml` — Services

| Service    | Image                          | Port(s)          | Purpose |
|------------|--------------------------------|------------------|---------|
| postgres   | `postgres:16-alpine`           | `5432`           | Primary database (experiments, runs, documents, artifacts) |
| redis      | `redis:7-alpine`               | `6379`           | Celery broker + result backend |
| mlflow     | `ghcr.io/mlflow/mlflow:latest` | `5000`           | Experiment tracking — records params, metrics, artifacts |
| langfuse   | `langfuse/langfuse:latest`     | `3000`           | LLM prompt tracing and observability |
| prometheus | `prom/prometheus:latest`       | `9090`           | Metrics scraping |
| grafana    | `grafana/grafana:latest`       | `3001`           | Dashboards (metrics + logs + traces) |
| loki       | `grafana/loki:latest`          | `3100`           | Log aggregation |
| tempo      | `grafana/tempo:latest`         | `3200`, `4317`   | Distributed tracing (OTLP gRPC on 4317) |

### Storage Backend — Backblaze B2

MLflow uses B2 as its artifact store via the S3-compatible API. The endpoint is constructed dynamically from `B2_REGION`:

```
s3.<B2_REGION>.backblazeb2.com
```

The `StorageService` in `shared/storage.py` handles uploads for the API and Worker with:
- Automatic multipart upload for files > 10 MB (prevents OOM on 16 GB primary device)
- Swappable backend via `storage_backend` config key (no code changes required)

### Volume Persistence

Two named volumes ensure data survives container restarts:
- `postgres_data` — all database tables
- `grafana_data` — dashboard configurations

### Health Checks

Both `postgres` and `redis` have health checks configured. MLflow and Langfuse use `depends_on: condition: service_healthy` to wait for postgres to be ready before starting.

### Storage Alternatives

| Backend    | When to use |
|------------|-------------|
| B2 (default) | Primary — S3-compatible, cheap egress |
| R2 (Cloudflare) | Alternative — zero egress cost |
| MinIO | Air-gapped / offline deployment (AGPL — internal only) |
| SeaweedFS | Self-hosted OSI-licensed alternative |
| LocalStack | Local dev / CI only |
| Filesystem | Earliest experiment runs before B2 configured |

---

## Files Changed

| File | Purpose |
|------|---------|
| `docker-compose.yml` | All service definitions with health checks and volumes |
| `shared/storage.py` | `StorageService`, `FilesystemStorageService`, `get_b2_client` |
| `infra/prometheus.yml` | Prometheus scrape config (mounted into container) |

---

## Usage

```bash
# Start all services
docker compose up -d

# Verify connectivity
curl http://localhost:5000    # MLflow
curl http://localhost:3000    # Langfuse
curl http://localhost:3001    # Grafana
```

---

## Acceptance Criteria Status

- [x] `docker compose up -d` completes without errors
- [x] `postgres` reachable at `localhost:5432`
- [x] `redis` reachable at `localhost:6379`
- [x] MLflow UI accessible at `http://localhost:5000`
- [x] Langfuse UI accessible at `http://localhost:3000`
- [x] Grafana accessible at `http://localhost:3001`
