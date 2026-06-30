"""Parse task stub — filled by AUD-021 / AUD-022."""
from celery import shared_task


@shared_task(name="worker.parse.document")
def parse_document(document_id: str, storage_key: str, config: dict) -> dict:
    """Download and parse a document. (Stub — AUD-021)"""
    return {"status": "stub", "document_id": document_id}
