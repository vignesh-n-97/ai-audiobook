# AUD-012 — Artifact Registry

**Epic:** EPIC 2 — Experiment Framework  
**Status:** 🔲 Stubbed (DB model defined; `ArtifactRegistry` not yet implemented)  
**Priority:** High  
**Depends on:** AUD-011  
**Blocks:** AUD-054  

---

## Summary

Provides `ArtifactRegistry`, which logs generated files (parsed markdown, audio chapters, metrics, traces) to MLflow (which proxies to Backblaze B2 as its artifact store). Every artifact is linked back to a `run_id` in the DB.

---

## What Was Implemented

### `Artifact` ORM Model (in `api/db/models.py`)

The `Artifact` table is defined and linked to `Run` via a foreign key. See AUD-010 documentation for the full column list.

Storage key pattern:

```
{run_id}/{artifact_type}/{filename}
```

| `artifact_type` | Extension | Example key |
|-----------------|-----------|-------------|
| `markdown` | `.md` | `{run_id}/markdown/{document_id}.md` |
| `audio` | `.mp3` | `{run_id}/audio/{chapter_id}.mp3` |
| `metrics` | `.json` | `{run_id}/metrics/summary.json` |
| `traces` | `.jsonl` | `{run_id}/traces/pipeline.jsonl` |

---

## Planned Implementation

```python
# api/services/artifact_service.py
from enum import StrEnum
import mlflow

class ArtifactType(StrEnum):
    MARKDOWN = "markdown"
    AUDIO = "audio"
    METRICS = "metrics"
    TRACES = "traces"

class ArtifactRegistry:
    def log(self, run_id: str, local_path: str, artifact_type: ArtifactType):
        """Logs file to MLflow (which uses B2 as artifact store)."""
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifact(local_path, artifact_path=artifact_type.value)

    def get_uri(self, run_id: str, artifact_type: ArtifactType, filename: str) -> str:
        return f"runs:/{run_id}/{artifact_type.value}/{filename}"
```

---

## Pending Implementation

- [ ] `ArtifactRegistry` class in `api/services/artifact_service.py`
- [ ] `ArtifactType` StrEnum
- [ ] `log()` method using `mlflow.log_artifact`
- [ ] DB record insertion in `artifacts` table after each log
- [ ] Integration into pipeline task (AUD-054)

---

## Acceptance Criteria Status

- [ ] Artifact uploaded during a run is retrievable via MLflow UI
- [ ] Each artifact record links back to its `run_id` in the DB
- [ ] Artifacts land in B2 bucket (verify via B2 dashboard or `b2 ls`)
