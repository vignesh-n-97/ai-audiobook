"""CRUD operations for Experiment and Run — AUD-010."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.experiment import Experiment, Run
from app.shared.schemas import PipelineConfig


class CRUDExperiment(CRUDBase[Experiment, Experiment]):
    """Experiment-specific CRUD operations."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Experiment | None:
        """Fetch an experiment by its unique name."""
        result = await db.execute(
            select(Experiment).where(Experiment.name == name)
        )
        return result.scalar_one_or_none()

    async def create_from_config(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str | None,
        pipeline_config: PipelineConfig,
    ) -> Experiment:
        """Create and persist an Experiment from a PipelineConfig.

        Stores the full config as a JSON blob for reproducibility.
        """
        obj = Experiment(
            name=name,
            description=description,
            pipeline_config=pipeline_config.model_dump(),
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj


class CRUDRun(CRUDBase[Run, Run]):
    """Run-specific CRUD operations."""

    async def get_runs_for_experiment(
        self,
        db: AsyncSession,
        *,
        experiment_id: uuid.UUID,
    ) -> list[Run]:
        """Return all runs for a given experiment, newest first."""
        result = await db.execute(
            select(Run)
            .where(Run.experiment_id == experiment_id)
            .order_by(Run.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_run(
        self,
        db: AsyncSession,
        *,
        experiment_id: uuid.UUID,
        mlflow_run_id: str,
        git_sha: str,
        branch: str,
        config_snapshot: dict,
        dataset_version: str | None = None,
    ) -> Run:
        """Insert a new Run record with status='running'."""
        obj = Run(
            experiment_id=experiment_id,
            mlflow_run_id=mlflow_run_id,
            git_sha=git_sha,
            branch=branch,
            status="running",
            config_snapshot=config_snapshot,
            dataset_version=dataset_version,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update_status(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
        status: str,
    ) -> Run | None:
        """Update the status of a run ('running' | 'completed' | 'failed')."""
        run = await self.get(db, run_id)
        if run is None:
            return None
        run.status = status  # type: ignore[assignment]
        await db.commit()
        await db.refresh(run)
        return run


experiment = CRUDExperiment(Experiment)
run = CRUDRun(Run)
