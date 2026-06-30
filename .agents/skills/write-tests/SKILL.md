# Write Tests Skill

Use this skill when you are explicitly asked to write tests for a module,
function, class, or pipeline stage in this repository.

---

## When This Skill Applies

This skill is invoked only when the user explicitly requests tests. Examples:

- "Write tests for the paragraph chunker"
- "Add tests for the experiment runner"
- "Add unit tests for the TTS adapter"

Do not invoke this skill speculatively. Do not add tests to a PR that did not
ask for them.

---

## Step 1 — Read the Source

Before writing any test:

1. Read the full source file under test
2. Identify all public methods and functions
3. Identify all raised exceptions
4. Identify all branches (if/else, try/except, early returns)
5. Identify all external dependencies (models, file I/O, HTTP, observability)

---

## Step 2 — Plan the Test Cases

For each public method or function, plan:

| Category | Question to answer |
|---|---|
| Happy path | What does it return for valid, expected input? |
| Failure path | What exceptions does it raise for invalid input or violated invariants? |
| Edge cases | What happens with empty input, zero, max values, None, missing optional fields? |

Write down the planned test cases before writing any code.

---

## Step 3 — Determine the Test File Location

Test files mirror the source path:

```
shared/chunkers/paragraph.py          → tests/shared/chunkers/test_paragraph.py
shared/tts/adapter.py                 → tests/shared/tts/test_adapter.py
shared/experiment/runner.py           → tests/shared/experiment/test_runner.py
api/routers/experiments.py            → tests/api/routers/test_experiments.py
worker/tasks/pipeline.py              → tests/worker/tasks/test_pipeline.py
```

If the test file already exists, add test cases to it — do not create a duplicate.

---

## Step 4 — Set Up Fixtures

Before writing test functions, define fixtures for:

- The unit under test (instantiated with mocked dependencies)
- Sample inputs (documents, chunks, config objects, `RunContext`)
- Expected outputs
- Mocked dependencies (model adapters, file I/O, observability emitters)

Place shared fixtures in the nearest `conftest.py` in the test directory hierarchy.

```python
# tests/shared/conftest.py

import pytest
from shared.chunkers.paragraph import ParagraphChunker
from shared.schemas import ChunkInput, RunContext

@pytest.fixture
def run_context() -> RunContext:
    return RunContext(
        run_id="test-run-001",
        experiment_id="test-exp-001",
        dataset_version="v1.0.0",
    )

@pytest.fixture
def chunker() -> ParagraphChunker:
    return ParagraphChunker(config={"max_tokens": 200, "overlap_tokens": 20})

@pytest.fixture
def sample_text() -> str:
    return "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
```

---

## Step 5 — Write Test Functions

### Naming

```python
def test_{unit}_{condition}(): ...
def test_{unit}_{condition}_{expected_result}(): ...
```

Examples:
```python
def test_paragraph_chunker_splits_on_double_newline(): ...
def test_paragraph_chunker_raises_on_empty_input(): ...
def test_paragraph_chunker_respects_max_token_limit(): ...
def test_tts_adapter_unloads_model_after_synthesis(): ...
def test_experiment_runner_writes_metadata_on_start(): ...
```

### Structure (AAA — Arrange, Act, Assert)

```python
def test_paragraph_chunker_splits_on_double_newline(chunker, sample_text, run_context):
    # Arrange
    input = ChunkInput(text=sample_text, run_context=run_context)

    # Act
    result = chunker.execute(input)

    # Assert
    assert len(result.chunks) == 3
    assert result.chunks[0].text == "First paragraph."
```

### Mocking external dependencies

```python
def test_tts_adapter_calls_model_with_chunk_text(mocker, run_context):
    mock_model = mocker.MagicMock()
    mock_model.synthesise.return_value = b"\x00\x01\x02"  # fake audio bytes

    adapter = KokoroTTSAdapter(model=mock_model, config={"voice": "af_sarah", "speed": 1.0})
    result = adapter.synthesise(text="Hello world.", run_context=run_context)

    mock_model.synthesise.assert_called_once_with("Hello world.", voice="af_sarah", speed=1.0)
    assert result.audio_bytes == b"\x00\x01\x02"
```

### Testing exceptions

```python
def test_paragraph_chunker_raises_on_empty_input(chunker, run_context):
    with pytest.raises(ValidationError, match="Input text cannot be empty"):
        chunker.execute(ChunkInput(text="", run_context=run_context))
```

### Testing model lifecycle (load → use → unload)

```python
def test_pipeline_stage_unloads_model_after_execution(mocker, run_context):
    mock_model = mocker.MagicMock()
    mocker.patch("shared.tts.kokoro.load_kokoro", return_value=mock_model)
    mock_gc = mocker.patch("gc.collect")

    stage = TTSStage(config={"voice": "af_sarah", "speed": 1.0})
    stage.execute(TTSInput(chunks=[Chunk(text="Hello")], run_context=run_context))

    # Model must be deleted and gc.collect must be called
    mock_gc.assert_called()
```

### Testing observability emissions

```python
def test_chunker_emits_stage_complete_event(mocker, chunker, sample_text, run_context):
    mock_emit = mocker.patch("shared.observability.emit_event")

    input = ChunkInput(text=sample_text, run_context=run_context)
    chunker.execute(input)

    mock_emit.assert_called_once()
    call_kwargs = mock_emit.call_args[1]
    assert call_kwargs["event_type"] == "chunk.execute.complete"
    assert call_kwargs["run_id"] == run_context.run_id
    assert "chunk_count" in call_kwargs["payload"]
```

---

## Step 6 — Validate Test Quality

Before submitting tests, verify:

- [ ] Every test is independent — no shared mutable state
- [ ] Every test is deterministic — no random data, no `time.time()` without mocking
- [ ] No real models are loaded
- [ ] No real file I/O outside `tmp_path`
- [ ] No real HTTP calls
- [ ] Happy path, failure path, and at least one edge case are covered per public method
- [ ] Test names read as plain English descriptions of behaviour
- [ ] All imports resolve correctly

Run locally:

```bash
pytest tests/shared/test_chunker.py -v
```

---

## Step 7 — Check Coverage (if requested)

If the user asks for coverage:

```bash
pytest tests/shared/chunkers/test_paragraph.py --cov=shared/chunkers/paragraph --cov-report=term-missing
```

Aim for ≥ 80% line coverage on the file under test. Report uncovered branches
to the user and ask whether to add tests for them.

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| Testing Python's own behaviour | Test your code's decisions, not `assert 1 + 1 == 2` |
| Overly broad `except Exception` mocks | Mock the specific exception type |
| Missing edge case: empty list input | Always test `[]`, `""`, `0`, `None` for optional fields |
| Forgetting to assert model was unloaded | Always verify teardown in model lifecycle tests |
| Checking mock call count instead of call args | Assert both count and argument values |
| Fixtures that create real files without `tmp_path` | Use `tmp_path` pytest fixture for file I/O |
