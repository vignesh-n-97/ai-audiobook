"""Experiments router — AUD-010.

Handles experiment CRUD and run listing.
Business logic (DB queries) lives in app/crud/experiments.py.
RunTracker integration (MLflow) is wired in AUD-011.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.experiments import experiment as crud_experiment
from app.crud.experiments import run as crud_run
from app.db.session import get_session
from app.shared.schemas import PipelineConfig

router = APIRouter(tags=["experiments"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ExperimentCreate(BaseModel):
    """Body for POST /experiments."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique experiment name")
    description: str | None = Field(None, description="Optional human-readable description")
    pipeline_config: PipelineConfig = Field(
        default_factory=PipelineConfig,
        description="Full pipeline configuration for this experiment",
    )


class ExperimentResponse(BaseModel):
    """Serialised experiment record returned by the API."""

    id: uuid.UUID
    name: str
    description: str | None
    pipeline_config: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunResponse(BaseModel):
    """Serialised run record returned by the API."""

    id: uuid.UUID
    experiment_id: uuid.UUID
    mlflow_run_id: str
    git_sha: str
    branch: str
    status: str
    config_snapshot: dict
    dataset_version: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    summary="Create an experiment",
    status_code=status.HTTP_201_CREATED,
    response_model=ExperimentResponse,
)
async def create_experiment(
    body: ExperimentCreate,
    db: AsyncSession = Depends(get_session),
) -> ExperimentResponse:
    """Create a new experiment from a PipelineConfig.

    The full ``pipeline_config`` is stored as a JSON blob so any future run
    can be reproduced given only this experiment's ID.
    Experiment names must be unique — a ``409`` is returned for duplicates.
    """
    existing = await crud_experiment.get_by_name(db, name=body.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experiment with name '{body.name}' already exists.",
        )

    experiment = await crud_experiment.create_from_config(
        db,
        name=body.name,
        description=body.description,
        pipeline_config=body.pipeline_config,
    )
    return ExperimentResponse.model_validate(experiment)


@router.get(
    "",
    summary="List experiments",
    response_model=list[ExperimentResponse],
)
async def list_experiments(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_session),
) -> list[ExperimentResponse]:
    """Return a paginated list of all experiments."""
    experiments = await crud_experiment.get_multi(db, skip=skip, limit=limit)
    return [ExperimentResponse.model_validate(e) for e in experiments]


@router.get(
    "/{experiment_id}",
    summary="Get a single experiment",
    response_model=ExperimentResponse,
)
async def get_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> ExperimentResponse:
    """Return a single experiment by its UUID."""
    experiment = await crud_experiment.get(db, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )
    return ExperimentResponse.model_validate(experiment)


@router.get(
    "/{experiment_id}/runs",
    summary="List runs for an experiment",
    response_model=list[RunResponse],
)
async def list_runs(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> list[RunResponse]:
    """Return all runs linked to a given experiment.

    Runs are ordered by creation time (newest first) by the CRUD layer.
    """
    experiment = await crud_experiment.get(db, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )
    runs = await crud_run.get_runs_for_experiment(db, experiment_id=experiment_id)
    return [RunResponse.model_validate(r) for r in runs]
