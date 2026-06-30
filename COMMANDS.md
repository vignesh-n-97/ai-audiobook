# AI Audiobook Platform — Command Reference

> Quick reference for all commands needed to develop, run, and manage the AI Audiobook platform.

---

## Prerequisites

```bash
# Verify installations
docker compose version
python3 --version   # 3.11+
```

---

## Environment Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

# 2. Install all dependencies
pip install -r requirements-dev.txt

# 3. Copy environment template and fill in your values
cp .env.example .env
```

---

## Docker Services

### Start All Services

```bash
# Start all infrastructure services in the background
docker compose up -d

# Start and follow logs
docker compose up
```

### Stop Services

```bash
# Stop all services (keep data volumes)
docker compose down

# Stop and remove data volumes (destructive — resets DB)
docker compose down -v
```

### Individual Services

```bash
# Start only specific services
docker compose up -d postgres redis
docker compose up -d mlflow langfuse
docker compose up -d grafana loki tempo prometheus

# Restart a single service
docker compose restart mlflow

# View logs for a service
docker compose logs -f mlflow
docker compose logs -f langfuse
```

### Service Status

```bash
docker compose ps
```

---

## Service URLs

| Service    | URL                        | Purpose                        |
|------------|----------------------------|--------------------------------|
| FastAPI    | http://localhost:8000      | REST API                       |
| API Docs   | http://localhost:8000/docs | Swagger UI                     |
| API ReDoc  | http://localhost:8000/redoc| ReDoc UI                       |
| MLflow     | http://localhost:5000      | Experiment tracking            |
| Langfuse   | http://localhost:3000      | LLM observability              |
| Grafana    | http://localhost:3001      | Metrics dashboards             |
| Prometheus | http://localhost:9090      | Metrics scraping               |
| Loki       | http://localhost:3100      | Log aggregation                |
| Tempo      | http://localhost:3200      | Distributed tracing            |
| LLMOps UI  | http://localhost:8501      | Experiment review (Streamlit)  |
| PostgreSQL | localhost:5432             | Primary database               |
| Redis      | localhost:6379             | Celery broker + result backend |

---

## FastAPI Server (app/)

```bash
# Development server with auto-reload
uvicorn app.application:app --reload --host 0.0.0.0 --port 8000

# Production (no reload)
uvicorn app.application:app --host 0.0.0.0 --port 8000 --workers 1
```

---

## Celery Worker (app/worker/)

```bash
# Start worker (concurrency=1 enforced — see AGENTS.md §Model Loading Policy)
celery -A app.worker.app:celery_app worker --loglevel=info --concurrency=1

# Start with structured JSON logs
celery -A app.worker.app:celery_app worker --loglevel=info --concurrency=1 2>&1 | jq .

# Monitor task queue (Flower UI at http://localhost:5555)
celery -A app.worker.app:celery_app flower --port=5555
```

---

## LLMOps UI (llmops/)

```bash
# Start Streamlit experiment review app
streamlit run llmops/main.py --server.port 8501
```

> Access at http://localhost:8501

---

## Database Migrations (Alembic)

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (auto-generates from model changes)
alembic revision --autogenerate -m "describe your change"

# Roll back last migration
alembic downgrade -1

# View current migration state
alembic current

# View migration history
alembic history
```

---

## Testing

```bash
# Run all tests
pytest tests/

# Run tests for a specific layer
pytest tests/api/
pytest tests/worker/
pytest tests/shared/

# Run with coverage report
pytest --cov=app --cov-report=term-missing tests/

# Run only smoke tests (fast)
pytest -m smoke

# Run with verbose output
pytest -v
```

---

## Code Quality

```bash
# Lint with ruff
ruff check .

# Fix auto-fixable lint issues
ruff check . --fix

# Type checking with mypy
mypy app/

# Format code
ruff format .

# Run pre-commit hooks manually (on all files)
pre-commit run --all-files

# Install pre-commit hooks (run once after clone)
pre-commit install
```

---

## Experiment Runs

```bash
# Trigger a pipeline run via the API
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/book.pdf"

# List experiments
curl http://localhost:8000/experiments

# View a specific run in MLflow
open http://localhost:5000

# Run an experiment script directly
python experiments/ke-001-voice-sweep.py
```

---

## Ollama (Local LLM)

```bash
# Pull a model (follow the tier ladder in TASKS.md)
ollama pull qwen2.5:0.5b    # Tier 1 — default start
ollama pull smollm2:1.7b    # Tier 3
ollama pull phi3:mini        # Tier 8

# List installed models
ollama list

# Test a model
ollama run qwen2.5:0.5b "Say hello"

# Start Ollama server (if not running as a service)
ollama serve
```

---

## Storage (Backblaze B2)

```bash
# Install b2 CLI
pip install b2

# Authorize account
b2 account authorize <keyId> <applicationKey>

# List bucket contents
b2 ls b2://<bucket-name>/

# List a specific prefix
b2 ls b2://<bucket-name>/uploads/

# Download a file
b2 file download b2://<bucket-name>/path/to/file ./local-file
```

---

## Useful Development Shortcuts

```bash
# Health check
curl http://localhost:8000/health | jq .

# Watch structured logs from API
uvicorn app.application:app --reload 2>&1 | jq .

# Inspect Celery task queue
celery -A app.worker.app:celery_app inspect active

# Purge all tasks from queue
celery -A app.worker.app:celery_app purge

# Connect to PostgreSQL
psql postgresql://audiobook:audiobook@localhost:5432/audiobook

# Connect to Redis CLI
redis-cli -u redis://localhost:6379
```

---

## Git Workflow

```bash
# Check current git SHA (used for run lineage)
git rev-parse HEAD

# Check current branch
git branch --show-current

# Create a feature branch
git checkout -b feature/aud-XXX-description

# Tag a release
git tag -a v0.1.0 -m "Baseline Kokoro pipeline"
git push origin v0.1.0
```
