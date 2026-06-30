"""Celery dispatch helpers — decouples API layer from worker internals."""

from __future__ import annotations

from celery import Celery

from app.shared.config import Config


def _get_celery() -> Celery:
    cfg = Config()
    return Celery(broker=cfg.celery_broker_url, backend=cfg.celery_result_backend)


def dispatch_pipeline(
    document_id: str,
    experiment_id: str,
    config: dict,
) -> str:
    """Send a pipeline run task to the Celery queue.

    Returns the Celery task ID for status polling.
    """
    result = _get_celery().send_task(
        "worker.pipeline.run",
        args=[document_id, experiment_id, config],
    )
    return result.id
