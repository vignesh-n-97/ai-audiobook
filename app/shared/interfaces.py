"""
Abstract base classes (ABCs) for all swappable pipeline components.

Every component in the pipeline — parsers, chunkers, TTS providers, LLM providers —
implements one of these interfaces. This ensures components are replaceable
without changing business logic (see AGENTS.md: Agent Decision Rule #14).

Usage pattern:
    parser = get_parser(cfg, ".pdf")  # factory returns a Parser
    result: ParseResult = parser.parse("/path/to/doc.pdf")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar, Type

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Document Parsing
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """Output of a document parser.

    Attributes:
        markdown:     Full document content as markdown string.
        metadata:     Parser-specific metadata (page count, headings, etc.).
        source_path:  Absolute path to the original source file.
        parser_name:  Identifies which parser produced this result (logged to MLflow).
    """

    markdown: str
    metadata: dict[str, Any]
    source_path: str
    parser_name: str


class Parser(ABC):
    """Abstract document parser.

    Implementations: DoclingParser, PDFPlumberParser, PyPDFParser,
    PyMuPDFParser, DocxParser, EpubParser.
    """

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        """Parse a document at *file_path* and return structured markdown."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """File extensions supported by this parser, e.g. ['.pdf']."""
        ...


# ---------------------------------------------------------------------------
# Chunking  (core domain — see AGENTS.md)
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single text chunk produced by a Chunker.

    Attributes:
        text:       The raw text content of this chunk.
        index:      Zero-based sequential position within the document.
        chunk_type: Semantic class — 'narration' | 'dialogue' | 'heading'.
        metadata:   Arbitrary chunk-level metadata (chapter title, speaker, etc.).
    """

    text: str
    index: int
    chunk_type: str  # "narration" | "dialogue" | "heading"
    metadata: dict[str, Any] = field(default_factory=dict)


class Chunker(ABC):
    """Abstract text chunker.

    Chunking is a primary research area. Implementations are configurable
    and measurable — never hardcode chunk sizes in business logic.

    Implementations: ParagraphChunker, SentenceChunker, SemanticChunker,
    DialogueChunker, AdaptiveChunker, HybridChunker.
    """

    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]:
        """Split *text* into a sequence of Chunk objects."""
        ...


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------

@dataclass
class AudioSegment:
    """Output of a TTS synthesis call.

    Attributes:
        audio_bytes:      Raw audio data (e.g. WAV/PCM bytes).
        sample_rate:      Sample rate in Hz (e.g. 24000).
        duration_seconds: Length of the audio clip.
        provider_name:    Identifies which TTS engine produced this segment.
    """

    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    provider_name: str


class TTSProvider(ABC):
    """Abstract TTS provider.

    Kokoro is the baseline provider (see AGENTS.md: Core Product Hypothesis).
    Implementations: KokoroProvider, PiperProvider, MeloTTSProvider.

    Model lifecycle: load → synthesize → unload.
    Never keep a model loaded between experiments without benchmark justification.
    """

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> AudioSegment:
        """Synthesize *text* into audio and return an AudioSegment."""
        ...

    @property
    @abstractmethod
    def available_voices(self) -> list[str]:
        """List of voice IDs available for this provider."""
        ...


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract LLM provider.

    All LLM execution targets local, open-weight models (Ollama / llamafile).
    Cloud inference is forbidden as a core dependency — see AGENTS.md.

    Implementations: OllamaProvider, LlamafileProvider.
    """

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send *prompt* to the LLM and return the raw text response."""
        ...

    @abstractmethod
    def complete_structured(self, prompt: str, schema: Type[T]) -> T:
        """Send *prompt* and parse the response into a Pydantic *schema* instance."""
        ...
