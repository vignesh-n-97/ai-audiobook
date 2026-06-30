"""
Shared package for the AI Audiobook platform.

Provides:
- Abstract base classes (interfaces) for Parser, Chunker, TTSProvider, LLMProvider
- Config loading via pydantic-settings
- Pydantic schemas (PipelineConfig, etc.)
- Storage service (B2 / S3-compatible)
- Common utilities
"""

__version__ = "0.1.0"
