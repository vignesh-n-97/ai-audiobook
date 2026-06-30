# Observability Rules

Extends AGENTS.md. Do not repeat rules defined there.

---

## Logging

### Logger

All logging goes through the centralised logger from `shared/observability/logger.py`.
Never call Python's `logging` module directly. Never use `print()` in production code.

```python
# Good
from shared.observability import get_logger
logger = get_logger(__name__)
logger.info("pipeline.parse.complete", extra={"run_id": run_id, "duration_ms": elapsed})

# Forbidden
print("Parse complete")
import logging; logging.info("Parse complete")
```

### Event name shape

Event names follow the same dot-separated domain pattern as AGENTS.md dictates:

```
{domain}.{event}                      pipeline.started, tts.complete
{domain}.{event}.{result}             model.load.success, model.load.failed
{domain}.{stage}.{lifecycle}          chunk.execute.start / .complete / .failed
```

Event names are stable across runs. Diagnostic details go into structured `extra`
fields — never in the message string.

### Domain prefixes

| Domain prefix | Used for |
|---|---|
| `pipeline.*` | Full pipeline lifecycle |
| `parse.*` | Document parsing stage |
| `ocr.*` | OCR execution |
| `chunk.*` | Chunking stage |
| `llm.*` | LLM prompt execution |
| `tts.*` | TTS synthesis |
| `audio.*` | Audio stitching and assembly |
| `eval.*` | Evaluation run |
| `model.*` | Model load / unload lifecycle |
| `experiment.*` | Experiment-level events |
| `run.*` | Run-level lifecycle events |
| `api.*` | FastAPI request/response events |
| `worker.*` | Celery task lifecycle |

### Log levels

| Level | Use for |
|---|---|
| `error` | Unrecoverable failures — pipeline crash, model load failure, audio assembly failure |
| `warning` | Recoverable degradations — retry attempt, fallback to CPU, missing optional config |
| `info` | Significant lifecycle events — run started, stage complete, artifact saved |
| `debug` | Diagnostic detail — chunk sizes, token counts, intermediate metrics |

### Structured extra fields

Every log event that relates to an experiment must include:

```python
extra = {
    "run_id": run_id,
    "experiment_id": experiment_id,
}
```

Stage-level events additionally include:
```python
extra = {
    "run_id": run_id,
    "experiment_id": experiment_id,
    "stage": "chunk",
    "duration_ms": elapsed_ms,
}
```

Model invocation events additionally include:
```python
extra = {
    "run_id": run_id,
    "model_name": model_name,
    "model_version": model_version,
    "execution_time_ms": elapsed_ms,
    "memory_usage_mb": peak_memory_mb,
}
```

### Forbidden logging patterns

- Prose messages: `logger.info("Document parsed successfully")` — use `"parse.complete"`
- Variable text in the message string: `logger.error(str(e))` — put it in `extra`
- `print()` anywhere in production code
- Logging PII: document text, user emails, file paths containing personal data
- Logging model weights or raw binary data

---

## Tracing

### Tracer

Use OpenTelemetry for distributed tracing. The tracer is initialised in
`shared/observability/tracer.py`.

```python
from shared.observability import get_tracer
tracer = get_tracer("pipeline")

with tracer.start_as_current_span("chunk.execute") as span:
    span.set_attribute("run_id", run_id)
    span.set_attribute("chunker", chunker_id)
    span.set_attribute("input_tokens", token_count)
    result = chunker.execute(input)
    span.set_attribute("chunk_count", len(result.chunks))
```

### What must be traced

Every pipeline stage must open a span:
- `parse.execute`
- `ocr.execute`
- `chunk.execute`
- `llm.invoke`
- `tts.synthesise`
- `audio.stitch`
- `eval.score`

Every span must include `run_id` and `experiment_id` as attributes.

### Trace backends

Preferred backends (self-hosted): Tempo, Langfuse, Arize Phoenix.
All backends are configurable — never hardcode an endpoint.
Backend selection comes from `shared/config.py`.

---

## Metrics

Use Prometheus (via `prometheus_client`) for metrics. The metrics registry is
initialised in `shared/observability/metrics.py`.

### Required metrics

| Metric | Type | Labels |
|---|---|---|
| `pipeline_run_duration_seconds` | Histogram | `experiment_id`, `status` |
| `stage_duration_seconds` | Histogram | `stage`, `run_id` |
| `model_load_duration_seconds` | Histogram | `model_name` |
| `model_memory_usage_mb` | Gauge | `model_name` |
| `chunks_generated_total` | Counter | `chunker`, `run_id` |
| `tts_synthesis_duration_seconds` | Histogram | `tts_id`, `run_id` |
| `audio_segments_total` | Counter | `run_id` |
| `eval_score` | Gauge | `metric_name`, `run_id` |

Metrics must be pushed to Prometheus Pushgateway from Celery workers (pull
scraping is not reliable for ephemeral workers).

---

## Events

Significant pipeline events are emitted as domain events and written to the
experiment's trace store.

```python
from shared.observability import emit_event

emit_event(
    event_type="pipeline.stage.complete",
    run_id=run_id,
    experiment_id=experiment_id,
    payload={
        "stage": "chunk",
        "chunker": chunker_id,
        "duration_ms": elapsed_ms,
        "chunk_count": len(chunks),
    }
)
```

---

## Context Propagation

`run_id` and `experiment_id` must be propagated to every function that emits
observability data. Do not rely on global/thread-local state.

Preferred pattern: pass a `RunContext` dataclass through the call chain.

```python
@dataclass
class RunContext:
    run_id: str
    experiment_id: str
    dataset_version: str
```

---

## A trace must answer (from AGENTS.md)

When reviewing a trace, it must be possible to answer:
- What happened?
- When did it happen?
- Why did it happen?
- Which inputs were used?
- Which outputs were generated?
- Which prompt was used?
- Which model was used?
- Which experiment was running?

If a trace cannot answer all of these questions, the stage's observability is
incomplete.
