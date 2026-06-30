"""Documents router — upload, list, get, and download endpoints."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.crud.documents import document as crud_document
from app.db.session import get_session
from app.models.document import Document
from app.shared.config import Config
from app.shared.storage import StorageService

router = APIRouter(tags=["documents"])

_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

# Both content-type and extension are checked so uploads work even when the
# browser sends a generic "application/octet-stream" content type.
_ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/epub+zip",
}
_ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".epub"}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    key: str
    original_filename: str
    size_bytes: int
    content_type: str


class DocumentResponse(BaseModel):
    """Full document record returned by list and get endpoints."""

    id: uuid.UUID
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    url: str
    key: str
    expires_in: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_upload(file: UploadFile) -> None:
    """Raise HTTPException for unsupported file types or oversized files."""
    filename = file.filename or ""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if file.content_type not in _ALLOWED_CONTENT_TYPES and ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                "Only .txt, .docx, .pdf, and .epub files are accepted."
            ),
        )

    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 500 MB limit.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="List documents",
    response_model=list[DocumentResponse],
)
async def list_documents(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    """Return a paginated list of all uploaded documents."""
    docs = await crud_document.get_multi(db, skip=skip, limit=limit)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get(
    "/{document_id}",
    summary="Get a document by ID",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """Return a single document record by its UUID."""
    doc = await crud_document.get(db, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return DocumentResponse.model_validate(doc)


@router.post(
    "/upload",
    summary="Upload a document",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    cfg: Config = Depends(get_config),
) -> DocumentUploadResponse:
    """Upload a PDF, DOCX, TXT, or EPUB document (max 500 MB).

    Files larger than 10 MB are streamed to Backblaze B2 in 5 MB chunks so
    the server never holds more than one chunk in memory at a time.
    The storage key is persisted to the ``documents`` table and returned in
    the response so callers can later request a pre-signed download URL.
    """
    _validate_upload(file)

    key = f"uploads/{uuid.uuid4()}/{file.filename or 'upload'}"
    storage = StorageService(cfg)

    # boto3 is synchronous — run the upload in a thread pool so the async
    # event loop is not blocked during the (potentially long) transfer.
    _url, actual_size = await asyncio.to_thread(
        storage.upload_fileobj,
        key,
        file.file,
        file.content_type or "application/octet-stream",
        file.size,
    )

    # Guard against cases where Content-Length was absent and the file turned
    # out to exceed the limit after being fully received.
    if actual_size > _MAX_UPLOAD_BYTES:
        await asyncio.to_thread(storage.delete, key)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 500 MB limit.",
        )

    doc = Document(
        original_filename=file.filename or key,
        storage_key=key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=actual_size,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return DocumentUploadResponse(
        id=doc.id,
        key=doc.storage_key,
        original_filename=doc.original_filename,
        size_bytes=doc.size_bytes,
        content_type=doc.content_type,
    )


@router.get(
    "/download",
    summary="Get a pre-signed download URL",
    response_model=DownloadUrlResponse,
)
async def download_document(
    key: str = Query(..., description="Storage key returned by the upload endpoint"),
    expires_in: int = Query(
        default=3600,
        ge=60,
        le=86400,
        description="URL validity window in seconds (60 s – 24 h)",
    ),
    cfg: Config = Depends(get_config),
) -> DownloadUrlResponse:
    """Return a pre-signed Backblaze B2 URL the browser can use to download a file.

    The URL embeds a ``Content-Disposition: attachment`` header so the browser
    saves the file locally rather than trying to render it inline.
    The URL is valid for *expires_in* seconds (default 1 hour, max 24 hours).
    """
    filename = key.split("/")[-1]
    storage = StorageService(cfg)

    url = await asyncio.to_thread(
        storage.presigned_download_url, key, filename, expires_in
    )

    return DownloadUrlResponse(url=url, key=key, expires_in=expires_in)
