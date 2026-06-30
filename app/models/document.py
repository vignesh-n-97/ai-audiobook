"""ORM model for uploaded source documents."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Document(Base):
    """An uploaded source document (PDF, DOCX, TXT).

    id, created_at, updated_at are inherited from Base.
    storage_key holds the B2 object key; use the download endpoint to obtain a presigned URL.
    """

    __tablename__ = "documents"

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
