---
trigger: manual
---

# Testing Rules

Extends AGENTS.md.

---

## When to Write Tests

**Tests are only written when explicitly requested.**

Do not add test files to a PR or task unless the user has asked for tests.
When tests are requested, use the skill defined in `.agents/skills/write-tests/SKILL.md`
to guide the process.

This rule exists because:
- Many tasks in this repository are exploratory experiments
- Test coverage requirements differ by component type
- Writing tests for every change would slow down experimentation velocity

---

## Test Framework

Framework: `pytest`
Configuration: `pyproject.toml` (`[tool.pytest.ini_options]`)
Test runner: `pytest` with `pytest-cov` for coverage

---

## Test Layout

Tests mirror the source structure. Every test file lives under `tests/`,
mirroring the top-level package path.

```
shared/config.py                    → tests/shared/test_config.py
shared/interfaces.py                → tests/shared/test_interfaces.py
shared/chunkers/paragraph.py        → tests/shared/chunkers/test_paragraph.py
api/routers/experiments.py          → tests/api/routers/test_experiments.py
api/routers/health.py               → tests/api/test_health.py
worker/tasks/pipeline.py            → tests/worker/tasks/test_pipeline.py
```

Naming: test files are named `test_{source_file_name}.py`. One source file
produces at most one test file.

---

## Test Categories

When tests are requested, cover these three categories for every unit:

| Category | What it proves |
|---|---|
| Unit tests | Correct output for valid, expected input |
| Failure tests | Correct errors raised for invalid input or violated invariants |
| Edge cases | Boundary values, empty inputs, max sizes, missing optional fields |

---

## What to Test by Layer

| Layer | Testing requirements |
|---|---|
| Domain models / business logic (`shared/`) | Happy path, invariant violations, edge cases — all external I/O mocked |
| Pipeline stages (`shared/experiment/`, `shared/ai/`) | Input/output contracts, error propagation — model calls mocked |
| Prompt templates (`shared/prompts/`) | Template rendering, variable injection, version metadata |
| FastAPI routers (`api/`) | HTTP method, status codes, request validation, error responses — service mocked |
| Celery tasks (`worker/`) | Payload handling, error propagation, idempotence — pipeline calls mocked |
| Observability utilities (`shared/observability/`) | Event emission, log formatting, metric registration |

---

## Test Rules

### Isolation

Each test is independent. No shared mutable state between tests.
Use `pytest` fixtures with function scope by default.

### Determinism

Same result on every run:
- No random data without seeding
- No `time.time()` or `datetime.now()` without mocking
- No real network calls, real file I/O, or real model inference

### Mocking

- Mock model inference: never run a real LLM or TTS model in tests
- Mock file I/O: use `tmp_path` fixture or `unittest.mock.patch`
- Mock observability: patch `emit_event` and `get_logger` to avoid side effects
- Mock external HTTP: use `respx` or `responses` for HTTP client mocking

```python
# Good — model is mocked
def test_chunker_emits_correct_chunk_count(mocker):
    mock_model = mocker.MagicMock()
    chunker = SemanticChunker(model=mock_model)
    result = chunker.execute(ChunkInput(text="Hello world. Goodbye world."))
    assert len(result.chunks) == 2

# Forbidden — real model loaded
def test_chunker_emits_correct_chunk_count():
    chunker = SemanticChunker(model=SentenceTransformer("all-MiniLM-L6-v2"))
    ...
```

### Test naming

Test functions use plain-English names that read as statements:

```python
def test_paragraph_chunker_splits_on_double_newline(): ...
def test_paragraph_chunker_raises_on_empty_input(): ...
def test_paragraph_chunker_respects_max_token_limit(): ...
```

Use `class`-based grouping only when the unit under test has many test cases:

```python
class TestParagraphChunker:
    def test_splits_on_double_newline(self): ...
    def test_raises_on_empty_input(self): ...
```

---

## Coverage

Coverage is tracked but not CI-enforced for the experimental research code
(`experiments/`, `notebooks/`).

For production code (`api/`, `worker/`, `shared/`), coverage is expected to
be ≥ 80% when tests are written. The threshold is enforced only when a PR
explicitly adds test coverage.

Coverage is checked locally with:

```bash
pytest --cov=api --cov=worker --cov=shared --cov-report=term-missing
```

---

## Integration Tests

Integration tests that exercise multiple components together live in:

```
tests/integration/
  test_paragraph_pipeline.py
  test_tts_adapter_kokoro.py
  ...
```

Integration tests:
- Are tagged `@pytest.mark.integration`
- Are excluded from the default `pytest` run
- Are run explicitly: `pytest -m integration`
- May use real file I/O on the local filesystem
- Must never make real HTTP calls to external services
- Must never load real neural network models (use quantized fixtures or mocks)

---

## Fixtures

Shared fixtures live in `tests/conftest.py` at the root level.
Package-level fixtures live in `tests/{name}/conftest.py` (e.g. `tests/shared/conftest.py`).

Common fixtures that must exist when tests are written:

```python
@pytest.fixture
def run_context() -> RunContext:
    return RunContext(
        run_id="test-run-001",
        experiment_id="test-experiment-001",
        dataset_version="v1.0.0",
    )

@pytest.fixture
def sample_document_text() -> str:
    return (Path(__file__).parent / "fixtures" / "sample.txt").read_text()
```

---

## Forbidden in Tests

- Real model inference (LLM, TTS, OCR, embedding models)
- Real external HTTP calls
- Hardcoded absolute paths
- `time.sleep()` in tests
- `assert True` or empty test bodies
- Tests that only test Python's own behaviour (e.g. `assert 1 + 1 == 2`)
- Shared mutable state between test functions
