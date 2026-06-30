# Architecture Rules

Extends AGENTS.md. Do not repeat rules defined there.

---

## Repository Layout

```
api/        FastAPI routers + dependency injection wiring
worker/     Celery task definitions + pipeline dispatch
llmops/     Streamlit read-only analysis UI
shared/     All domain logic, interfaces, schemas, config, storage
tests/      All tests — mirrors api/, worker/, shared/
```

### shared/ — implementation lives here

`shared/` owns everything that is not routing, task dispatch, or UI:

- Domain interfaces and ABCs (`shared/interfaces.py`)
- Pydantic schemas (`shared/schemas.py`)
- Configuration (`shared/config.py`)
- Storage utilities (`shared/storage.py`)
- Logging helpers (`shared/logging.py`)
- Chunking strategies
- Parser adapters
- TTS adapters
- LLM adapters
- Evaluation functions
- Experiment runner

**Forbidden inside `api/` or `worker/`:**
- Domain model classes
- Chunking logic
- OCR logic
- TTS logic
- Prompt templates
- Evaluation scoring
- Experiment configuration parsing

If you find yourself writing business logic in `api/` or `worker/`, extract it to `shared/` first.

---

## FastAPI Layer Rules (api/)

### Router structure

Every feature area gets its own router file:

```
api/routers/
  experiments.py
  runs.py
  documents.py
  artifacts.py
  health.py
```

Routers are mounted in `api/main.py` — nowhere else.

### Dependency injection

Use FastAPI `Depends()` to inject services. Never instantiate a service or
shared class inside a route handler body.

```python
# Good
@router.post("/experiments")
async def create_experiment(
    payload: ExperimentCreate,
    service: ExperimentService = Depends(get_experiment_service),
):
    return await service.create(payload)

# Forbidden — service instantiated inside handler
@router.post("/experiments")
async def create_experiment(payload: ExperimentCreate):
    service = ExperimentService()   # ← wrong
    return await service.create(payload)
```

### Route handlers must not contain business logic

Route handlers:
- Parse and validate request data (FastAPI + Pydantic handles this)
- Call exactly one service method
- Return the response

If a handler is longer than 15 lines, business logic has leaked into the router.

---

## Worker Layer Rules (worker/)

### Celery task definitions

Tasks are thin dispatch functions. They call pipeline functions defined in `shared/`.

```python
# Good
@celery_app.task(name="run_pipeline")
def run_pipeline_task(run_id: str) -> None:
    pipeline = PipelineRunner.from_run_id(run_id)
    pipeline.execute()

# Forbidden — pipeline logic inside task
@celery_app.task(name="run_pipeline")
def run_pipeline_task(run_id: str) -> None:
    doc = load_document(run_id)       # ← business logic in task
    chunks = split_into_paragraphs(doc)
    ...
```

### Task idempotence

Every task must be idempotent. Running the same task twice with the same
`run_id` must produce the same result or detect duplication and skip.

### Model lifecycle inside tasks

Follow the model loading policy from AGENTS.md. Tasks must:
1. Load the model
2. Execute the task
3. Unload the model (explicit `del model`, `gc.collect()`, CUDA cache clear if GPU)

Never retain a model reference across task boundaries.

---

## Cross-Module Import Rules

- `api/` may import from `shared/`
- `worker/` may import from `shared/`
- `llmops/` may import from `shared/` (read-only, schemas + config only)
- `shared/` must never import from `api/`, `worker/`, or `llmops/`
- `api/` and `worker/` must not import from each other

Circular imports are forbidden.

---

## General Rules

Always:
- Keep `api/` and `worker/` thin — orchestration only
- Put domain and pipeline logic in `shared/`
- Use FastAPI `Depends()` for all service injection
- Follow the model load → execute → unload lifecycle in workers

Never:
- Write chunking, OCR, TTS, or LLM logic inside `api/` or `worker/`
- Import `api/` or `worker/` code from `shared/`
- Retain model references across Celery task boundaries
- Hardcode experiment parameters — they belong in experiment YAML configs
