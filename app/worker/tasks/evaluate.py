"""Evaluate task stub — filled by AUD-050."""
from celery import shared_task


@shared_task(name="worker.evaluate.run")
def evaluate_run(run_id: str, config: dict) -> dict:
    """Evaluate audio quality for a completed run. (Stub — AUD-050)"""
    return {"status": "stub", "run_id": run_id}
