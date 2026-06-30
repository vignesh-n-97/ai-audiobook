"""
Pipeline orchestration task — top-level entry point for a full run.

This task orchestrates the pipeline stages in sequence:
  parse → chunk → [llm_enrich] → tts → evaluate

It does not implement any stage logic itself — that belongs in app/shared/.
Every run creates an MLflow run for full experiment lineage (AUD-011).
"""

from __future__ import annotations

import contextlib
import uuid

import structlog
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.shared.config import Config
from app.shared.schemas import PipelineConfig

log = structlog.get_logger(__name__)


def _get_sync_session(cfg: Config) -> Session:
    """Create a synchronous SQLAlchemy session for use inside Celery tasks.

    Celery workers are synchronous — we cannot use the async session from
    app/db/session.py here. The sync URL replaces 'postgresql+asyncpg' with
    'postgresql+psycopg2' (or bare 'postgresql') so psycopg2 is used.
    """
    sync_url = cfg.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    return Session(engine)


@shared_task(bind=True, name="worker.pipeline.run")
def run_pipeline(self, document_id: str, experiment_id: str, config: dict) -> dict:
    """Execute a full audiobook pipeline for *document_id*.

    Args:
        document_id:   UUID of the uploaded document.
        experiment_id: UUID of the parent experiment.
        config:        Serialised PipelineConfig dict.

    Returns:
        dict with run_id and output artifact locations.
    """
    pipeline_cfg = PipelineConfig(**config)
    cfg = Config()

    log.info(
        "pipeline.started",
        document_id=document_id,
        experiment_id=experiment_id,
        chunker=pipeline_cfg.chunker,
        tts_provider=pipeline_cfg.tts_provider,
        llm_model=pipeline_cfg.llm_model,
    )

    from app.services.run_service import RunTracker  # lazy import

    tracker = RunTracker(tracking_uri=cfg.mlflow_tracking_uri)
    db = _get_sync_session(cfg)

    # Retrieve experiment name for MLflow (fall back to experiment_id if not found)
    try:
        from app.models.experiment import Experiment
        exp = db.get(Experiment, uuid.UUID(experiment_id))
        experiment_name = exp.name if exp else experiment_id
    except Exception:
        experiment_name = experiment_id

    mlflow_run_id = "unknown"
    db_run_id: uuid.UUID | None = None

    try:
        mlflow_run_id, db_run_id = tracker.start_run_sync(
            db,
            experiment_name=experiment_name,
            experiment_id=uuid.UUID(experiment_id),
            config=pipeline_cfg,
        )

        # TODO (AUD-021): dispatch parse task
        # TODO (AUD-030): dispatch chunk task
        # TODO (AUD-040): dispatch tts task
        # TODO (AUD-050): dispatch evaluate task

        tracker.end_run_sync(
            db,
            db_run_id=db_run_id,
            mlflow_run_id=mlflow_run_id,
            status="FINISHED",
        )

        log.info(
            "pipeline.completed",
            document_id=document_id,
            mlflow_run_id=mlflow_run_id,
            db_run_id=str(db_run_id),
        )
        return {
            "status": "completed",
            "document_id": document_id,
            "mlflow_run_id": mlflow_run_id,
            "db_run_id": str(db_run_id),
        }

    except Exception as exc:
        log.error(
            "pipeline.failed",
            document_id=document_id,
            error=str(exc),
            exc_info=True,
        )
        if db_run_id is not None:
            with contextlib.suppress(Exception):
                tracker.end_run_sync(
                    db,
                    db_run_id=db_run_id,
                    mlflow_run_id=mlflow_run_id,
                    status="FAILED",
                )
        raise

    finally:
        db.close()
