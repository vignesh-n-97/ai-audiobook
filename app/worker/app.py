"""
Celery application factory for the AI Audiobook Worker.

Workers execute pipelines — they do not define business rules.
All business logic lives in app/shared/.

Worker responsibilities (per AGENTS.md):
  - pipeline execution
  - OCR execution
  - parsing execution
  - chunking execution
  - model execution
  - TTS execution
  - evaluation execution
  - batch experimentation

Model lifecycle within a task:
  Load → Execute → Collect Metrics → Emit Trace → Unload
Only one major model should occupy memory at a time.
"""

from __future__ import annotations

from celery import Celery

from app.shared.config import Config

cfg = Config()

celery_app = Celery(
    "worker",
    broker=cfg.celery_broker_url,
    backend=cfg.celery_result_backend,
    include=[
        "app.worker.tasks.pipeline",
        "app.worker.tasks.parse",
        "app.worker.tasks.chunk",
        "app.worker.tasks.tts",
        "app.worker.tasks.evaluate",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Enforce sequential model execution — see AGENTS.md §Model Loading Policy
    worker_concurrency=1,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
