"""
Centralised configuration for the AI Audiobook platform.

All swappable components read their implementation from this config.
No component should contain if-provider-name branches in business logic —
use factories that accept a Config instance.

Loading order:
  1. Default values defined here
  2. Environment variables (uppercase, no prefix)
  3. .env file (if present)

See TASKS.md §Config Loading Pattern for the full factory pattern.
"""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path | str:
    """Find the .env file in parent directories."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return ".env"


class Config(BaseSettings):
    """Platform-wide configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Storage (Primary: Backblaze B2 — S3-compatible API)
    # ------------------------------------------------------------------
    storage_backend: str = "b2"  # b2 | r2 | minio | seaweedfs | filesystem

    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_id: str = ""
    b2_bucket_name: str = ""
    b2_region: str = "us-west-004"  # Encoded in endpoint: s3.<region>.backblazeb2.com

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------
    pdf_parser: str = "docling"     # docling | pdfplumber | pypdf | pymupdf
    ocr_backend: str = "rapidocr"  # rapidocr | easyocr | paddleocr | tesseract

    # ------------------------------------------------------------------
    # Chunker  (core domain)
    # ------------------------------------------------------------------
    chunker: str = "paragraph"     # paragraph | sentence | semantic | dialogue | adaptive | hybrid
    chunk_max_chars: int = 800

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------
    tts_provider: str = "kokoro"   # kokoro | piper | melotts
    tts_voice: str = "af_bella"
    tts_speed: float = 1.0

    # ------------------------------------------------------------------
    # LLM  (local-only — no cloud APIs as core dependencies)
    # ------------------------------------------------------------------
    llm_runtime: str = "ollama"          # ollama | llamafile
    llm_model: str = "qwen2.5:0.5b"     # Follow tier ladder in TASKS.md
    llm_orchestration: str = "langgraph" # langgraph | dspy | haystack
    llm_structured_output: str = "pydantic_ai"  # pydantic_ai | outlines | instructor

    # ------------------------------------------------------------------
    # NLP utilities
    # ------------------------------------------------------------------
    sentence_detector: str = "spacy"  # spacy | nltk | stanza | nnsplit
    g2p_backend: str = "espeak"       # espeak | gruut | g2p_en

    # ------------------------------------------------------------------
    # Experiment tracking & observability
    # ------------------------------------------------------------------
    mlflow_tracking_uri: str = "http://localhost:5000"
    langfuse_host: str = "http://localhost:3000"

    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "ai-audiobook"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://audiobook:audiobook@localhost:5432/audiobook"

    # ------------------------------------------------------------------
    # Redis / Celery
    # ------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    git_sha: str = "unknown"
