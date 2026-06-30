"""
Pydantic schemas shared across the platform.

These schemas travel across service boundaries (API ↔ Worker ↔ packages).
Keep them serialisable — no domain logic here.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Declarative configuration for a single pipeline execution.

    Every experiment is reproducible because the full PipelineConfig
    is stored as a JSON blob alongside the run record (see AGENTS.md).

    Values must match keys in shared.config.Config so experiments can
    be loaded directly from YAML files in experiments/.
    """

    # Parser
    pdf_parser: str = "docling"
    ocr_backend: str = "rapidocr"

    # Chunker
    chunker: str = "paragraph"
    chunk_max_chars: int = 800

    # TTS
    tts_provider: str = "kokoro"
    tts_voice: str = "af_bella"
    tts_speed: float = 1.0

    # LLM
    llm_model: str = "qwen2.5:0.5b"
    llm_orchestration: str = "langgraph"
    llm_structured_output: str = "pydantic_ai"

    # NLP
    sentence_detector: str = "spacy"
    g2p_backend: str = "espeak"

    # DSP / audio post-processing
    dsp_preset: str = "default"

    # Escape hatch for future keys — never use for switching implementations
    extra: dict[str, Any] = Field(default_factory=dict)


class ExperimentYAML(BaseModel):
    """Schema for experiment definition files stored in experiments/*.yaml."""

    name: str
    description: str | None = None
    pipeline_config: PipelineConfig = Field(default_factory=PipelineConfig)


class RunRecord(BaseModel):
    """Lightweight run summary stored in the DB and returned by the API."""

    run_id: str
    experiment_id: str
    mlflow_run_id: str
    git_sha: str
    branch: str
    status: str  # "running" | "completed" | "failed"
    config_snapshot: PipelineConfig


class ArtifactRecord(BaseModel):
    """Tracks a single generated artifact back to its producing run."""

    artifact_id: str
    source_run_id: str
    artifact_type: str   # "markdown" | "audio" | "metrics" | "traces"
    storage_key: str
    creation_timestamp: str
