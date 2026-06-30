# Worker Pipeline Rules

Extends AGENTS.md. Covers Celery worker architecture, pipeline stage
implementation, model lifecycle, and audio assembly.

---

## Worker Responsibilities (from AGENTS.md)

Workers execute pipelines. Workers do not define business rules.

The worker (`worker/`) is responsible for:
- Receiving task payloads from the task queue
- Dispatching to the correct pipeline runner
- Collecting and emitting results
- Writing artifacts to `runs/{run_id}/`

Business logic lives in `shared/`. Workers call `shared/`.

---

## Celery Configuration

```python
# worker/celery_app.py
from celery import Celery

celery_app = Celery(
    "audiobook_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.config_from_object("worker.celery_config")
```

Task queues:
- `pipeline` — full pipeline execution tasks
- `evaluation` — evaluation-only tasks
- `batch` — batch experiment execution

Each queue has its own worker pool to prevent batch jobs from starving pipeline jobs.

---

## Task Definitions

Tasks are thin. All logic is in `shared/`.

```python
# Good
@celery_app.task(name="pipeline.run", queue="pipeline", bind=True)
def run_pipeline(self, run_id: str, config_path: str) -> dict:
    try:
        config = load_experiment_config(config_path)
        runner = PipelineRunner(config=config, run_id=run_id)
        result = runner.execute()
        return result.model_dump()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)
```

### Task rules

- Tasks accept only serialisable arguments (strings, ints, dicts — no objects)
- `run_id` is always passed as an argument — never generated inside a task
- Every task logs its start, completion, and failure with `run_id`
- Tasks use `bind=True` to access `self.retry()` for transient failures
- Permanent failures (bad config, missing input) must not retry — raise immediately
- Transient failures (model load OOM, file lock, network) may retry with backoff

---

## Pipeline Stage Execution Order

```
1. Document Upload / Validation
2. Document Parsing (parser adapter)
3. OCR Execution (optional, if scanned PDF)
4. Text Normalisation (optional, if LLM configured)
5. Chunking (chunker strategy from config)
6. Prosody Preparation (optional, if LLM configured)
7. TTS Synthesis (per chunk, sequential)
8. Audio Assembly (stitch chunks → final audiobook)
9. Evaluation (optional, if evaluation config present)
10. Artifact Save + Run Metadata Write
```

Each stage is implemented as a class in `shared/`. The runner executes them in
order, passing typed outputs from one stage as inputs to the next.

---

## Model Lifecycle

Follow AGENTS.md model loading policy strictly.

```python
# Good — explicit load → execute → unload
def run_tts_stage(input: TTSInput, run_context: RunContext) -> TTSOutput:
    logger.info("tts.load.start", extra={"run_id": run_context.run_id})
    model = load_kokoro(device="cpu")
    try:
        result = synthesise_all_chunks(model, input.chunks)
        return TTSOutput(audio_segments=result)
    finally:
        del model
        import gc; gc.collect()
        logger.info("tts.unload.complete", extra={"run_id": run_context.run_id})
```

Never:
- Cache a model instance as a module-level global
- Assume GPU memory is available without checking
- Load two major models simultaneously

---

## Chunking Implementation

Chunking is a core domain (see AGENTS.md). Implementation rules:

### Chunker interface

```python
class BaseChunker(ABC):
    @abstractmethod
    def execute(self, input: ChunkInput) -> ChunkOutput:
        """
        Split input text into chunks according to the strategy.
        Must respect max_tokens from config — never hardcode.
        """
        ...
```

### Rules

- `max_tokens` comes from the experiment config — never hardcoded
- Every chunker records: `chunk_count`, `avg_tokens_per_chunk`,
  `min_tokens`, `max_tokens` in the stage metrics
- Chunks are numbered sequentially and written to `runs/{run_id}/chunks/`
- Each chunk file includes: `chunk_id`, `index`, `text`, `token_count`,
  `source_paragraph`, `chunker_id`, `run_id`

### Chunker registration

New chunking strategies are registered in the component registry
(`shared/experiment/registry.py`). They are not added by
modifying pipeline code.

---

## Audio Assembly

Audio assembly stitches per-chunk audio files into a final audiobook.

Rules:
- Assembly is its own pipeline stage — not part of TTS synthesis
- Input: ordered list of audio segment file paths from `runs/{run_id}/audio/`
- Output: `runs/{run_id}/audio/audiobook.wav` (and optionally `.mp3`)
- Silence padding between chunks is configurable (not hardcoded)
- Assembly must be resumable: if some chunks are already synthesised, skip them
- The assembled file path and checksum are recorded in `runs/{run_id}/metadata.json`

---

## Batch Experimentation

Batch experiments run multiple experiment configs sequentially against the same
dataset version.

```python
# worker/tasks/batch_task.py

@celery_app.task(name="batch.run_experiments", queue="batch")
def run_experiment_batch(config_paths: list[str], dataset_version: str) -> list[dict]:
    results = []
    for config_path in config_paths:
        run_id = str(uuid4())
        result = run_pipeline.apply(args=[run_id, config_path])
        results.append({"run_id": run_id, "status": result.status})
    return results
```

Rules:
- Experiments in a batch share the same `dataset_version`
- Each experiment in a batch gets its own `run_id`
- Batch tasks run in the `batch` queue to avoid starving individual pipeline jobs
- A failure in one batch experiment must not abort the remaining experiments

---

## Error Handling in Workers

- Pipeline errors are caught, logged with full context, and recorded in
  `runs/{run_id}/metadata.json` as `status: "failed"`
- Transient errors trigger Celery retry with exponential backoff
- Permanent errors (invalid config, missing file) are recorded and not retried
- Every caught exception includes `run_id` in the log extra fields

```python
try:
    runner.execute()
except ConfigurationError as e:
    logger.error("run.failed.config_error", extra={"run_id": run_id, "error": e.message})
    write_failed_run_metadata(run_id, reason=e.message)
    raise  # do not retry — config errors are permanent
except PipelineError as e:
    logger.error("run.failed.pipeline_error", extra={"run_id": run_id, "error": e.message})
    raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
```

---

## Resource Management

Given hardware constraints (see AGENTS.md):

- Never load a model without first checking available memory
- Prefer streaming synthesis over loading an entire document into memory
- Process chunks sequentially — do not parallelise across chunks on the same machine
- After each major stage, call `gc.collect()` to free memory before the next stage
- Use `psutil` to log memory usage before and after model load

```python
import psutil, gc

def get_memory_mb() -> float:
    return psutil.Process().memory_info().rss / 1024 / 1024

before_mb = get_memory_mb()
model = load_model()
after_mb = get_memory_mb()
logger.info("model.load.complete", extra={
    "model_name": model_name,
    "memory_delta_mb": after_mb - before_mb,
    "total_memory_mb": after_mb,
})
```

---

## Forbidden in Workers

- Business logic (chunking algorithms, evaluation scoring, prompt construction)
- Importing from `api/` — workers and API are independent applications
- Global model instances that persist across task executions
- Parallel model loading (`ThreadPoolExecutor` with multiple models)
- Hardcoded stage order — order comes from the pipeline runner
- Writing directly to `artifacts/` — all outputs go to `runs/{run_id}/`
