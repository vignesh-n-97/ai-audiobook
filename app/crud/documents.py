"""CRUD operations for Document — stub, filled by AUD-020."""

from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.document import Document


class CRUDDocument(CRUDBase[Document, Document]):
    pass


document = CRUDDocument(Document)
