"""ArtifactRegistry — AUD-012.

Logs pipeline-generated files to MLflow (which proxies to B2 as its artifact store)
and persists a record in the local DB so every artifact can be traced back to its run.

Artifact types and storage key conventions:
    markdown  → {db_run_id}/markdown/{filename}.md
    audio     → {db_run_id}/audio/{filename}.mp3
    metrics   → {db_run_id}/metrics/{filename}.json
    traces    → {db_run_id}/traces/{filename}.jsonl

Usage (worker context — sync session):
    registry = ArtifactRegistry(tracking_uri=cfg.mlflow_tracking_uri)
    artifact = registry.log_sync(
        db,
        mlflow_run_id=mlflow_run_id,
        db_run_id=db_run_id,
        local_path="/tmp/chapter1.mp3",
        artifact_type=ArtifactType.AUDIO,
    )
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from pathlib import Path

import mlflow
import structlog

log = structlog.get_logger(__name__)


class ArtifactType(StrEnum):
    MARKDOWN = "markdown"
    AUDIO = "audio"
    METRICS = "metrics"
    TRACES = "traces"


class ArtifactRegistry:
    """Logs artifacts to MLflow and records them in the DB.

    Two session modes mirror RunTracker:
        log()       — async, for FastAPI context.
        log_sync()  — sync, for Celery worker context.
    """

    def __init__(self, tracking_uri: str) -> None:
        self._tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    # ------------------------------------------------------------------
    # Async API (FastAPI context)
    # ------------------------------------------------------------------

    async def log(
        self,
        db,  # AsyncSession
        *,
        mlflow_run_id: str,
        db_run_id: uuid.UUID,
        local_path: str,
        artifact_type: ArtifactType,
    ):
        """Log a file to MLflow and insert an Artifact DB record.

        Returns the persisted Artifact ORM instance.
        """
        from app.models.artifact import Artifact

        storage_key = self._log_to_mlflow(
            mlflow_run_id=mlflow_run_id,
            db_run_id=db_run_id,
            local_path=local_path,
            artifact_type=artifact_type,
        )

        artifact = Artifact(
            run_id=db_run_id,
            artifact_type=artifact_type.value,
            storage_key=storage_key,
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        log.info(
            "artifact.logged",
            artifact_id=str(artifact.id),
            artifact_type=artifact_type.value,
            storage_key=storage_key,
            db_run_id=str(db_run_id),
        )
        return artifact

    # ------------------------------------------------------------------
    # Sync API (Celery worker context)
    # ------------------------------------------------------------------

    def log_sync(
        self,
        db,  # sync Session
        *,
        mlflow_run_id: str,
        db_run_id: uuid.UUID,
        local_path: str,
        artifact_type: ArtifactType,
    ):
        """Synchronous variant for Celery workers."""
        from app.models.artifact import Artifact

        storage_key = self._log_to_mlflow(
            mlflow_run_id=mlflow_run_id,
            db_run_id=db_run_id,
            local_path=local_path,
            artifact_type=artifact_type,
        )

        artifact = Artifact(
            run_id=db_run_id,
            artifact_type=artifact_type.value,
            storage_key=storage_key,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        log.info(
            "artifact.logged",
            artifact_id=str(artifact.id),
            artifact_type=artifact_type.value,
            storage_key=storage_key,
            db_run_id=str(db_run_id),
        )
        return artifact

    # ------------------------------------------------------------------
    # URI helpers
    # ------------------------------------------------------------------

    def get_uri(
        self,
        mlflow_run_id: str,
        artifact_type: ArtifactType,
        filename: str,
    ) -> str:
        """Return an MLflow artifact URI for a given run + type + filename."""
        return f"runs:/{mlflow_run_id}/{artifact_type.value}/{filename}"

    def get_storage_key(
        self,
        db_run_id: uuid.UUID,
        artifact_type: ArtifactType,
        filename: str,
    ) -> str:
        """Return the canonical B2 storage key for an artifact."""
        return f"{db_run_id}/{artifact_type.value}/{filename}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_to_mlflow(
        self,
        *,
        mlflow_run_id: str,
        db_run_id: uuid.UUID,
        local_path: str,
        artifact_type: ArtifactType,
    ) -> str:
        """Upload *local_path* to MLflow under *artifact_type* folder.

        MLflow proxies the upload to B2 when configured with an S3 artifact store.
        Returns the storage key string derived from db_run_id.
        """
        filename = Path(local_path).name
        try:
            with mlflow.start_run(run_id=mlflow_run_id):
                mlflow.log_artifact(local_path, artifact_path=artifact_type.value)
        except Exception as exc:
            # Log but do not crash — the DB record is still useful for lineage
            log.warning(
                "artifact.mlflow_log_failed",
                local_path=local_path,
                error=str(exc),
            )

        return self.get_storage_key(db_run_id, artifact_type, filename)
