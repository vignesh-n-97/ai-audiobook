# AUD-054 — Audiobook Generation Pipeline

**Epic:** EPIC 6 — Baseline Audiobook Generation  
**Status:** 🔲 Scaffolded (Celery task registered; stages not yet wired)  
**Priority:** Critical  
**Depends on:** AUD-011, AUD-012, AUD-040, AUD-053  
**Blocks:** AUD-060  

---

## Summary

The top-level Celery task that orchestrates the full audiobook pipeline: download → parse → detect chapters → chunk → TTS → stitch → upload. Every run creates a traceable MLflow run with full lineage.

---

## What Was Implemented

### Celery Worker Application (`worker/app.py`)

```python
celery_app = Celery(
    "worker",
    broker=cfg.celery_broker_url,
    backend=cfg.celery_result_backend,
    include=[
        "worker.tasks.pipeline",
        "worker.tasks.parse",
        "worker.tasks.chunk",
        "worker.tasks.tts",
        "worker.tasks.evaluate",
    ],
)
```

Key configuration enforcing the CPU-first / sequential model loading policy (AGENTS.md §Model Loading Policy):
```python
worker_concurrency=1          # only one task at a time
task_acks_late=True           # ack after completion, not pickup
worker_prefetch_multiplier=1  # don't buffer tasks
```

### Registered Tasks

| Module | Task Name | Status |
|--------|-----------|--------|
| `worker.tasks.pipeline` | `worker.pipeline.run` | ✅ Scaffolded |
| `worker.tasks.parse` | `worker.parse.run` | 🔲 Stub |
| `worker.tasks.chunk` | `worker.chunk.run` | 🔲 Stub |
| `worker.tasks.tts` | `worker.tts.run` | 🔲 Stub |
| `worker.tasks.evaluate` | `worker.evaluate.run` | 🔲 Stub |

### Pipeline Task Scaffold (`worker/tasks/pipeline.py`)

```python
@shared_task(bind=True, name="worker.pipeline.run")
def run_pipeline(self, document_id: str, experiment_id: str, config: dict) -> dict:
    pipeline_cfg = PipelineConfig(**config)
    log.info("pipeline.started", ...)
    # TODO (AUD-011): start MLflow run
    # TODO (AUD-021): parse task
    # TODO (AUD-030): chapter detection
    # TODO (AUD-040): chunk task
    # TODO (AUD-050): tts task
    # TODO (AUD-060): evaluate task
    log.info("pipeline.completed", ...)
    return {"status": "stub", "document_id": document_id}
```

---

## Full Pipeline Flow (Planned)

```
Document ID
    ↓
Download from B2             (StorageService.download)
    ↓
Parse → ParseResult          (get_parser(cfg, ext).parse(path))
    ↓
Chapter Detection            (ChapterDetector.detect(markdown))
    ↓
For each Chapter:
    Chunk → list[Chunk]      (get_chunker(cfg).chunk(chapter.text))
    For each Chunk:
        TTS → AudioSegment   (get_tts_provider(cfg).synthesize(chunk.text))
    Stitch → chapter.mp3     (AudioStitcher.stitch(segments))
    Upload to B2             (ArtifactRegistry.log(..., AUDIO))
    ↓
End MLflow run (FINISHED)
```

On any exception:
```
End MLflow run (FAILED)
Celery retry (max 1)
```

---

## Pending Implementation

- [ ] `RunTracker.start_run()` call at pipeline start (AUD-011)
- [ ] `StorageService.download()` to fetch source document
- [ ] Parser dispatch (AUD-021)
- [ ] Chapter detector call (AUD-030)
- [ ] Chunker dispatch (AUD-040)
- [ ] TTS dispatch (AUD-050)
- [ ] Audio stitching per chapter (AUD-053)
- [ ] `ArtifactRegistry.log()` for each chapter MP3 (AUD-012)
- [ ] `RunTracker.end_run("FAILED")` in exception handler

---

## Acceptance Criteria Status

- [ ] A full PDF generates one MP3 per chapter in B2
- [ ] Run is logged in MLflow with all config params
- [ ] Failed run is marked `FAILED` in MLflow and DB
- [ ] Re-running with a different `PipelineConfig` creates a new MLflow run (not overwriting)
