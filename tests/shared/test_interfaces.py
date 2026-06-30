"""Tests for shared.interfaces — smoke tests only."""

from app.shared.interfaces import ParseResult, Chunk, AudioSegment


def test_parse_result_creation() -> None:
    result = ParseResult(
        markdown="# Hello",
        metadata={"page_count": 1},
        source_path="/tmp/test.pdf",
        parser_name="mock",
    )
    assert result.markdown == "# Hello"
    assert result.parser_name == "mock"


def test_chunk_creation() -> None:
    chunk = Chunk(text="Hello world", index=0, chunk_type="narration")
    assert chunk.chunk_type == "narration"
    assert chunk.metadata == {}


def test_audio_segment_creation() -> None:
    seg = AudioSegment(
        audio_bytes=b"\x00\x01",
        sample_rate=24000,
        duration_seconds=0.5,
        provider_name="mock",
    )
    assert seg.sample_rate == 24000
