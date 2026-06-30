# Python Rules

Extends AGENTS.md. Covers Python-specific engineering standards for this
monorepo (FastAPI, Pydantic, Celery, async).

---

## Language and Version

- Python 3.11+
- Type hints are mandatory on all function signatures
- `from __future__ import annotations` is used in all modules for forward-reference compatibility

---

## Type Hints

Type hints are required on every function, method, and class attribute. There
are no exceptions.

```python
# Good
def execute(self, input: ChunkInput, *, run_context: RunContext) -> ChunkOutput:
    ...

# Forbidden
def execute(self, input, run_context):
    ...
```

- Never use `Any` from `typing` — narrow the type instead
- Never use bare `dict` or `list` — always parameterise: `dict[str, str]`, `list[Chunk]`
- Use `TypeAlias` for complex repeated types
- Use `TypedDict` or Pydantic models for structured dicts — never raw `dict[str, Any]`
- Use `Protocol` for structural subtyping of pipeline stages and adapters

---

## Pydantic Models

Use Pydantic v2 for all data models, request/response schemas, and
configuration.

### Rules

- All API request and response schemas are Pydantic `BaseModel` subclasses
- `model_config = ConfigDict(frozen=True)` on immutable value objects
- `model_config = ConfigDict(extra="forbid")` on all input models — reject unknown fields
- Validators use `@field_validator` (Pydantic v2 style) — not `@validator`
- Never use `dict()` to access model data — use attribute access or `model_dump()`

```python
# Good
class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    pipeline_config: PipelineConfig

# Forbidden
class ExperimentCreate(BaseModel):
    name: str
    description: str
    # missing extra="forbid" — unknown keys silently accepted
```

---

## FastAPI Specifics

### Response models

Every route must declare an explicit `response_model`. Never return raw dicts.

```python
@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(...) -> ExperimentResponse:
    ...
```

### Error handling

Raise `HTTPException` only in route handlers. Business logic in `shared/`
raises domain-specific exceptions (subclasses of `shared.errors.AppError`).
The FastAPI exception handler in `api/main.py` converts `AppError` to
`HTTPException`.

Never catch a broad `Exception` and swallow it silently.

### Async

- Route handlers are `async def` when they await any I/O
- CPU-bound pipeline operations run in a `ThreadPoolExecutor` via
  `asyncio.run_in_executor()` — never block the event loop
- Do not use `asyncio.sleep()` as a retry delay — use `tenacity` for retries

---

## Error Classes

Domain errors live in `shared/errors.py`:

```python
class AppError(Exception):
    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

class NotFoundError(AppError): ...
class ConflictError(AppError): ...
class ValidationError(AppError): ...
class ConfigurationError(AppError): ...
class PipelineError(AppError): ...
class ModelLoadError(AppError): ...
```

- Raise the most specific error class available
- Never raise bare `Exception` or `RuntimeError` from business logic
- Always include a human-readable message and a machine-readable `code`

---

## Configuration

All configuration comes through Pydantic `BaseSettings` in
`shared/config.py`.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    database_url: str
    redis_url: str
    model_cache_dir: Path
    log_level: str = "info"
```

- Never read `os.environ` directly — always use the Settings instance
- Never hardcode file paths — use `Path` objects resolved from settings
- Never hardcode model names or versions — they come from settings or experiment config

---

## Code Quality

### Function length

Functions must not exceed **50 lines**. Split at logical boundaries.

### Nesting depth

Maximum nesting depth is **3 levels**. Use early returns to flatten.

```python
# Good — flat with early returns
def process_chunk(chunk: Chunk) -> str:
    if not chunk.text:
        return ""
    if chunk.is_empty():
        return ""
    return normalise(chunk.text)

# Forbidden — deep nesting
def process_chunk(chunk: Chunk) -> str:
    if chunk.text:
        if not chunk.is_empty():
            return normalise(chunk.text)
    return ""
```

### Single responsibility

If a function name contains "and", split it.

### Immutability preference

Prefer immutable data structures. Use `tuple` over `list` for fixed-length
sequences. Use frozen Pydantic models for value objects.

---

## Imports

- Imports are sorted: stdlib → third-party → internal packages → relative
  (use `isort` or ruff with `known_first_party = ["api", "worker", "shared", "llmops"]`)
- No wildcard imports (`from module import *`)
- No circular imports — enforce with `import-linter`
- Internal packages are imported by their public `__init__.py` interface only

---

## Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Modules | `snake_case` | `chunker_service.py` |
| Classes | `PascalCase` | `ParagraphChunker` |
| Functions / methods | `snake_case` | `execute_pipeline()` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_CHUNK_SIZE` |
| Type aliases | `PascalCase` | `ChunkList = list[Chunk]` |
| Pydantic models | `PascalCase` | `ExperimentConfig` |
| Private members | `_leading_underscore` | `_load_model()` |

---

## Async and Concurrency

- Never block the FastAPI event loop with synchronous I/O
- Run model inference (CPU or GPU) in a `ThreadPoolExecutor`
- Celery tasks are always synchronous (`def`, not `async def`) — Celery does not
  support async tasks without a custom event loop setup
- Use `asyncio.gather()` only when operations are genuinely independent and bounded

---

## Dependency Management

- All dependencies are declared in `requirements.txt` (runtime) and `requirements-dev.txt` (dev + test)
- A single venv covers the entire project — no per-package installs
- Minimum version pins only (no upper bounds) unless a known incompatibility exists
- GPU dependencies (`torch` CUDA, etc.) go in a separate `requirements-gpu.txt` — never in `requirements.txt`
- The base install must work on CPU-only hardware

```bash
# Set up the project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

---

## Forbidden

- `Any` type in production code
- `print()` in production code — use the observability logger
- `os.environ` reads outside `shared/config.py`
- Hardcoded model paths, chunk sizes, or experiment parameters
- Mutable default arguments (`def fn(x: list = [])`)
- `except Exception: pass` — swallowing errors silently
- Synchronous file I/O or model loading on the FastAPI event loop
