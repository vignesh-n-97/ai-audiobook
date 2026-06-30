"""
ORM models for experiments and runs.

Experiment and Run are co-located to avoid circular imports via back_populates.
id, created_at, updated_at are inherited from Base.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.artifact import Artifact


class Experiment(Base):
    """A named, reproducible pipeline configuration.

    One experiment can have many runs executed against it.
    The pipeline_config JSON stores the full PipelineConfig so any run
    can be reconstructed given only its experiment_id.
    """

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    runs: Mapped[list[Run]] = relationship("Run", back_populates="experiment")


class Run(Base):
    """A single pipeline execution — always linked to an Experiment.

    Every run captures full lineage: git SHA, branch, config snapshot.
    Given a run ID the entire execution can be reconstructed.
    See AGENTS.md §Reproducibility Requirements.
    """

    __tablename__ = "runs"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False
    )
    mlflow_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="running"
    )  # running | completed | failed
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="runs")
    artifacts: Mapped[list[Artifact]] = relationship("Artifact", back_populates="run")
