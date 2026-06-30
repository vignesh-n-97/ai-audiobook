"""Worker smoke test."""

from app.worker.tasks.pipeline import run_pipeline


def test_run_pipeline_task_is_registered() -> None:
    """Verify the pipeline task can be imported without error."""
    assert run_pipeline.name == "worker.pipeline.run"
