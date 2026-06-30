"""Tests for shared.schemas."""

from app.shared.schemas import PipelineConfig, ExperimentYAML
import yaml


def test_pipeline_config_defaults() -> None:
    cfg = PipelineConfig()
    assert cfg.chunker == "paragraph"
    assert cfg.tts_provider == "kokoro"
    assert cfg.llm_model == "qwen2.5:0.5b"


def test_pipeline_config_from_yaml() -> None:
    raw = """
name: baseline-kokoro-v1
description: Paragraph chunker + Kokoro default voice
pipeline_config:
  pdf_parser: docling
  chunker: paragraph
  tts_provider: kokoro
  tts_voice: af_bella
  tts_speed: 1.0
  llm_model: qwen2.5:0.5b
"""
    data = yaml.safe_load(raw)
    experiment = ExperimentYAML(**data)
    assert experiment.name == "baseline-kokoro-v1"
    assert experiment.pipeline_config.tts_provider == "kokoro"
