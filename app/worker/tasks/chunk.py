"""Chunk task stub — filled by AUD-030."""
from celery import shared_task


@shared_task(name="worker.chunk.text")
def chunk_text(markdown: str, config: dict) -> dict:
    """Chunk parsed markdown. (Stub — AUD-030)"""
    return {"status": "stub", "chunk_count": 0}
