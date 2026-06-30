# Architecture Overview

## Repository Structure

See `AGENTS.md` for the authoritative architecture decisions and rules.

```
ai-audiobook/
├── api/        FastAPI service — routing and orchestration only
├── worker/     Celery workers — pipeline execution only
├── llmops/     Streamlit experiment review UI — read-only
├── shared/     Domain logic, interfaces, schemas, config, storage
├── tests/      All tests (mirrors api/, worker/, shared/)
├── experiments/  Experiment YAML configs
├── datasets/   Benchmark corpora and evaluation sets
├── artifacts/  Versioned model/audio artifacts
├── runs/       Run outputs (gitignored large files)
└── infra/      Prometheus config etc.
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker + Docker Compose

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — add your B2 credentials
```

### 2. Start infrastructure

```bash
docker compose up -d
```

Services:
| Service    | URL                    |
|------------|------------------------|
| Postgres   | localhost:5432         |
| Redis      | localhost:6379         |
| MLflow     | http://localhost:5000  |
| Langfuse   | http://localhost:3000  |
| Grafana    | http://localhost:3001  |
| Prometheus | http://localhost:9090  |
| Tempo      | localhost:4317 (gRPC)  |

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 4. Run the API

```bash
uvicorn api.main:app --reload --port 8000
```

`GET http://localhost:8000/health` should return `{"status": "healthy", ...}`.

### 5. Run the worker

```bash
celery -A worker.app:celery_app worker --loglevel=info --concurrency=1
```

### 6. Run the LLMOps UI

```bash
streamlit run llmops/main.py --server.port 8501
```

## Running Tests

```bash
pytest tests/
pytest tests/api/
pytest tests/worker/
pytest tests/shared/
```

## Experiment Files

Experiments are declared as YAML files in `experiments/`. See
`experiments/baseline-kokoro-v1.yaml` for the reference format.

## Key Design Decisions

1. **CPU-first** — all features must work without a GPU.
2. **No cloud AI APIs** — only local models via Ollama/llamafile.
3. **Chunking is a core domain** — never hardcode chunk sizes.
4. **Observability is mandatory** — every stage emits logs, traces, metrics.
5. **Business logic lives in `shared/`** — `api/` and `worker/` only orchestrate.
6. **Single venv** — one `requirements.txt` for the entire project; no per-package Poetry.
