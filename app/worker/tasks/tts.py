"""TTS task stub — filled by AUD-040."""
from celery import shared_task


@shared_task(name="worker.tts.synthesize")
def synthesize_audio(chunks: list, config: dict) -> dict:
    """Synthesize audio for text chunks. (Stub — AUD-040)"""
    return {"status": "stub", "segment_count": 0}
