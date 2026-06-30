# AUD-011 — Run Tracking

**Epic:** EPIC 2 — Experiment Framework  
**Status:** 🔲 Stubbed (task registered; `RunTracker` not yet implemented)  
**Priority:** High  
**Depends on:** AUD-010  
**Blocks:** AUD-012, AUD-054  

---

## Summary

Every pipeline execution must be a traceable MLflow run. This ticket implements `RunTracker`, which creates MLflow runs, logs `PipelineConfig` as params, captures git lineage (`git_sha`, `branch`), and marks runs as `FAILED` on exception.

---

## What Was Implemented

### Pipeline Task Scaffold (`worker/tasks/pipeline.py`)

The Celery task `worker.pipeline.run` is registered and accepts the arguments needed for run tracking:

```python
@shared_task(bind=True, name="worker.pipeline.run")
def run_pipeline(self, document_id: str, experiment_id: str, config: dict) -> dict:
    pipeline_cfg = PipelineConfig(**config)
    # TODO (AUD-011): initialise RunTracker, start MLflow run
    ...
```

Structured logging is wired up — every pipeline invocation logs:
- `document_id`
- `experiment_id`
- `chunker`
- `tts_provider`
- `llm_model`

### Run-Tracking API Design (specified; not yet wired)

```python
# api/services/run_service.py  (planned)
class RunTracker:
    def start_run(self, experiment_name: str, config: PipelineConfig) -> str:
        # Capture git_sha + branch via subprocess
        # mlflow.set_experiment(experiment_name)
        # mlflow.start_run() → log all PipelineConfig fields as params
        # Return MLflow run_id

    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None): ...
    def end_run(self, run_id: str, status: str = "FINISHED"): ...
```

---

## Pending Implementation

- [ ] `RunTracker` class in `api/services/run_service.py`
- [ ] `git rev-parse HEAD` and `git branch --show-current` capture in `start_run`
- [ ] MLflow run creation with full `PipelineConfig` as params
- [ ] Exception handler in pipeline task that calls `end_run(..., "FAILED")`
- [ ] `mlflow_run_id` stored in `runs` DB table

---

## Acceptance Criteria Status

- [ ] Every pipeline run creates an MLflow run with `git_sha`, `branch`, `timestamp`, and full `PipelineConfig` as params
- [ ] Failed runs are marked `FAILED` in MLflow
- [ ] Run ID stored in `runs` DB table linked to `experiment_id`
