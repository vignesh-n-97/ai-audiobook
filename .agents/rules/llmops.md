# LLMOps Rules

Extends AGENTS.md. Covers the `llmops/` application and the tooling stack
used for experiment tracking, trace inspection, and model comparison.

---

## Purpose

`llmops/` is a read-only analysis application. It exists for humans to
review experiments — not to run them.

It must not:
- Trigger pipeline executions
- Modify experiment configs
- Write to `runs/` or `artifacts/`
- Call model inference endpoints

---

## Preferred Self-Hosted Stack

The following tools are preferred for the LLMOps stack. All are self-hosted.
Selection and configuration come from `infra/`.

| Tool | Purpose |
|---|---|
| **MLflow** | Experiment tracking, run comparison, metric history |
| **Langfuse** | Prompt tracing, LLM invocation logging, prompt version review |
| **Arize Phoenix** | LLM observability, embedding drift, evaluation visualisation |
| **OpenTelemetry** | Distributed tracing (spans exported to Tempo) |
| **Prometheus** | Metrics collection from pipeline runs |
| **Grafana** | Dashboard for metrics, logs, and run health |
| **Loki** | Log aggregation (structured JSON logs from all apps and workers) |
| **Tempo** | Trace storage backend for OpenTelemetry spans |

All tools are replaceable. Never hardcode a specific tool's SDK into
`shared/` — adapters live in `shared/observability/` and are swappable.

---

## MLflow Integration

### Experiment tracking

Every pipeline run registers a run in MLflow:

```python
import mlflow

with mlflow.start_run(run_name=run_id, experiment_name=experiment_name):
    mlflow.log_params({
        "parser": config.pipeline.parser,
        "chunker": config.pipeline.chunker,
        "llm": config.pipeline.llm,
        "tts": config.pipeline.tts,
        "dataset_version": config.dataset.version,
        "git_commit_sha": git_commit_sha,
    })

    # ... run pipeline stages ...

    mlflow.log_metrics({
        "parse_duration_ms": parse_duration,
        "chunk_count": chunk_count,
        "tts_duration_ms": tts_duration,
        "eval_mos_score": mos_score,
    })

    mlflow.log_artifact(f"runs/{run_id}/audiobook.wav")
    mlflow.log_artifact(f"runs/{run_id}/config.yaml")
```

### Rules

- Every completed run has a corresponding MLflow run record
- Params are experiment configuration values — not runtime internals
- Metrics are numeric measurements — not string labels
- Artifacts logged to MLflow are copies — the canonical copy stays in `runs/{run_id}/`

---

## Langfuse Integration

Every LLM prompt invocation is logged to Langfuse:

```python
from langfuse import Langfuse

langfuse = Langfuse()

trace = langfuse.trace(
    name="normalise_text",
    metadata={
        "run_id": run_id,
        "experiment_id": experiment_id,
        "prompt_id": template.prompt_id,
        "prompt_version": template.version,
    }
)

generation = trace.generation(
    name=f"{template.prompt_id}@{template.version}",
    model=model_name,
    model_parameters={"temperature": 0.0},
    prompt=rendered_prompt,
    completion=model_response,
    usage={"input": input_tokens, "output": output_tokens},
)
```

The Langfuse adapter wraps this logic in `shared/observability/langfuse_adapter.py`.
Pipeline code calls the adapter — it does not call Langfuse directly.

---

## Experiment Comparison

Experiments are compared in `llmops/` using the MLflow tracking API.

Comparison is valid only when:
- `dataset.version` is identical across compared runs
- Evaluation metrics were collected by the same evaluation function version

The LLMOps UI must surface `dataset.version` prominently to prevent invalid
comparisons.

---

## Evaluation Metrics

The platform tracks these primary evaluation metrics:

| Metric | Description | Range |
|---|---|---|
| `mos_score` | Mean Opinion Score (audio quality) | 1–5 |
| `word_error_rate` | WER against reference transcript | 0–1 (lower is better) |
| `naturalness` | Prosody naturalness score | 0–1 |
| `chunk_coherence` | Semantic coherence of chunk boundaries | 0–1 |
| `tts_duration_ratio` | TTS synthesis time / audio duration | lower is better |

Evaluation functions live in `shared/evaluation/`.
New metrics must be added there — not computed ad hoc in notebooks.

---

## Benchmark Reporting

Benchmark reports compare a set of experiment runs against a baseline.

Rules:
- Baseline is the earliest run in the comparison set (by timestamp)
- Improvements are percentage deltas from the baseline
- Reports are generated as HTML artifacts saved to `artifacts/reports/`
- Report generation is triggered manually — never automatically on run completion

---

## Prompt Review Workflow

When a prompt change is proposed:

1. Create a new prompt version in `shared/prompts/`
2. Run a comparison experiment (old version vs. new version)
3. Review both traces in Langfuse
4. Compare evaluation metrics in MLflow
5. Document the decision in the experiment config's `description` field

The LLMOps UI surfaces this workflow by linking prompt versions to their
associated experiment runs.

---

## Trace Inspection Requirements

A trace inspection in `llmops/` must show:

For a pipeline run:
- Full stage breakdown (parse → chunk → llm → tts → assemble)
- Duration and memory usage per stage
- Chunk count and statistics
- Model names and versions used

For a prompt invocation:
- Prompt ID and version
- Rendered prompt (full text)
- Model response (full text)
- Token counts (input + output)
- Latency

If a trace cannot show all of the above, the corresponding pipeline stage's
observability is incomplete.

---

## Audio Review

`llmops/` provides an audio review interface that allows:
- Playback of individual chunk audio segments
- Side-by-side playback of the same chunk across different experiment runs
- Display of the source text alongside the audio
- Display of which TTS config and voice were used

Audio files are served from `runs/{run_id}/audio/`. The LLMOps app reads them
— it does not copy or re-encode them.

---

## Forbidden in LLMOps

- Triggering pipeline execution or model inference
- Writing to `runs/`, `artifacts/`, `datasets/`, or `experiments/`
- Fetching raw model weights or prompt templates from the UI
- Exposing unauthenticated access to run data in production
- Implementing experiment comparison logic — that belongs in `shared/evaluation/`
