"""RunTracker — AUD-011.

Orchestrates MLflow run lifecycle and persists run lineage to the DB.

Design notes:
- This service lives in app/services/ as a thin orchestration helper.
- All git capture is wrapped in try/except so the tracker never crashes
  in environments without a .git directory (Docker, CI without checkout).
- Two session modes:
    async_session (AsyncSession) — used by FastAPI routes.
    sync_session  (Session)      — used by Celery workers (synchronous).
  Pass whichever is appropriate for the calling context.
"""

from __future__ import annotations

import subprocess
import uuid

import mlflow
import structlog

from app.shared.schemas import PipelineConfig

log = structlog.get_logger(__name__)

# Type alias covering both async and sync SQLAlchemy sessions.
# Workers use sync sessions; the API uses async sessions.
_AnySession = object  # resolved at runtime via duck-typing


def _capture_git_sha() -> str:
    """Return the current HEAD git SHA, or 'unknown' if git is unavailable."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _capture_git_branch() -> str:
    """Return the current git branch name, or 'unknown' if unavailable."""
    try:
        return (
            subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        ) or "unknown"
    except Exception:
        return "unknown"


class RunTracker:
    """Manages MLflow run lifecycle and DB run records.

    Usage (worker context — sync session)::

        tracker = RunTracker(tracking_uri="http://localhost:5000")
        mlflow_id, db_id = tracker.start_run_sync(
            db_session, experiment_name=experiment_name,
            experiment_id=experiment_id, config=config,
        )
        try:
            ...
            tracker.end_run_sync(db_session, db_id, mlflow_id, "FINISHED")
        except Exception:
            tracker.end_run_sync(db_session, db_id, mlflow_id, "FAILED")
            raise

    Usage (API context — async session):
        tracker = RunTracker(cfg=cfg, tracking_uri=cfg.mlflow_tracking_uri)
        mlflow_id, db_id = await tracker.start_run(db_session, ...)
    """

    def __init__(self, tracking_uri: str) -> None:
        self._tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    # ------------------------------------------------------------------
    # Async API (FastAPI context)
    # ------------------------------------------------------------------

    async def start_run(
        self,
        db,  # AsyncSession
        *,
        experiment_name: str,
        experiment_id: uuid.UUID,
        config: PipelineConfig,
        dataset_version: str | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Start an MLflow run and insert a Run record. Returns (mlflow_run_id, db_run_id)."""
        from app.crud.experiments import run as crud_run  # lazy — avoids circular import

        git_sha = _capture_git_sha()
        branch = _capture_git_branch()

        mlflow_run_id, config_dict = self._mlflow_start(
            experiment_name=experiment_name,
            config=config,
            git_sha=git_sha,
            branch=branch,
        )

        db_run = await crud_run.create_run(
            db,
            experiment_id=experiment_id,
            mlflow_run_id=mlflow_run_id,
            git_sha=git_sha,
            branch=branch,
            config_snapshot=config_dict,
            dataset_version=dataset_version,
        )

        log.info(
            "run.started",
            mlflow_run_id=mlflow_run_id,
            db_run_id=str(db_run.id),
            experiment_id=str(experiment_id),
            git_sha=git_sha,
            branch=branch,
        )
        return mlflow_run_id, db_run.id

    async def end_run(
        self,
        db,  # AsyncSession
        *,
        db_run_id: uuid.UUID,
        mlflow_run_id: str,
        status: str = "FINISHED",
    ) -> None:
        """End the MLflow run and update the DB run status."""
        from app.crud.experiments import run as crud_run

        self._mlflow_end(mlflow_run_id=mlflow_run_id, status=status)
        await crud_run.update_status(db, run_id=db_run_id, status=status.lower())
        log.info("run.ended", mlflow_run_id=mlflow_run_id, db_run_id=str(db_run_id), status=status)

    # ------------------------------------------------------------------
    # Sync API (Celery worker context)
    # ------------------------------------------------------------------

    def start_run_sync(
        self,
        db,  # sync Session
        *,
        experiment_name: str,
        experiment_id: uuid.UUID,
        config: PipelineConfig,
        dataset_version: str | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Synchronous variant for Celery workers."""
        from app.models.experiment import Run

        git_sha = _capture_git_sha()
        branch = _capture_git_branch()

        mlflow_run_id, config_dict = self._mlflow_start(
            experiment_name=experiment_name,
            config=config,
            git_sha=git_sha,
            branch=branch,
        )

        run = Run(
            experiment_id=experiment_id,
            mlflow_run_id=mlflow_run_id,
            git_sha=git_sha,
            branch=branch,
            status="running",
            config_snapshot=config_dict,
            dataset_version=dataset_version,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        log.info(
            "run.started",
            mlflow_run_id=mlflow_run_id,
            db_run_id=str(run.id),
            experiment_id=str(experiment_id),
            git_sha=git_sha,
            branch=branch,
        )
        return mlflow_run_id, run.id

    def end_run_sync(
        self,
        db,  # sync Session
        *,
        db_run_id: uuid.UUID,
        mlflow_run_id: str,
        status: str = "FINISHED",
    ) -> None:
        """Synchronous variant of end_run for Celery workers."""
        from app.models.experiment import Run

        self._mlflow_end(mlflow_run_id=mlflow_run_id, status=status)

        run = db.get(Run, db_run_id)
        if run is not None:
            run.status = status.lower()
            db.commit()

        log.info("run.ended", mlflow_run_id=mlflow_run_id, db_run_id=str(db_run_id), status=status)

    # ------------------------------------------------------------------
    # Metric logging (works in both contexts — mlflow is synchronous)
    # ------------------------------------------------------------------

    def log_metric(
        self,
        mlflow_run_id: str,
        key: str,
        value: float,
        step: int | None = None,
    ) -> None:
        """Log a single metric to the active MLflow run."""
        with mlflow.start_run(run_id=mlflow_run_id):
            mlflow.log_metric(key, value, step=step)

    def log_metrics(self, mlflow_run_id: str, metrics: dict[str, float]) -> None:
        """Log multiple metrics in one call."""
        with mlflow.start_run(run_id=mlflow_run_id):
            mlflow.log_metrics(metrics)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mlflow_start(
        self,
        *,
        experiment_name: str,
        config: PipelineConfig,
        git_sha: str,
        branch: str,
    ) -> tuple[str, dict]:
        """Create an MLflow experiment (if needed) and start a run.

        Returns (mlflow_run_id, config_dict).
        """
        config_dict = config.model_dump()
        mlflow.set_experiment(experiment_name)
        run = mlflow.start_run()
        mlflow.log_params(config_dict)
        mlflow.set_tags({"git_sha": git_sha, "branch": branch})
        # Do NOT end the run here — caller is responsible
        return run.info.run_id, config_dict

    @staticmethod
    def _mlflow_end(*, mlflow_run_id: str, status: str) -> None:
        """End an MLflow run by ID. Maps DB status strings to MLflow status strings."""
        mlflow_status = {
            "FINISHED": "FINISHED",
            "FAILED": "FAILED",
            "completed": "FINISHED",
            "failed": "FAILED",
        }.get(status.upper(), "FINISHED")

        try:
            with mlflow.start_run(run_id=mlflow_run_id):
                mlflow.end_run(status=mlflow_status)
        except Exception as exc:
            # Never let MLflow failure prevent DB cleanup
            log.warning("run.mlflow_end_failed", mlflow_run_id=mlflow_run_id, error=str(exc))
