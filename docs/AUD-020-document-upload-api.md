# AUD-020 — Document Upload API

**Epic:** EPIC 3 — Document Ingestion  
**Status:** 🔲 Stub registered  
**Priority:** High  
**Depends on:** AUD-003, AUD-012  
**Blocks:** AUD-021  

---

## Summary

Provides `POST /documents/upload` — a multipart file upload endpoint that validates the file extension, streams the file to Backblaze B2 storage, and returns a `document_id` for downstream pipeline use.

---

## What Was Implemented

### Stub Router (`api/routers/documents.py`)

The router is registered at `/documents`. Endpoint is a stub pending full implementation.

### `StorageService` (`shared/storage.py`)

The upload infrastructure is fully implemented and reusable:

```python
class StorageService:
    def upload(self, key: str, data: bytes | IO, content_type: str) -> str:
        # Files > 10 MB → multipart upload (5 MB parts)
        # Files ≤ 10 MB → single PUT
        # Returns public URL
```

**Multipart upload strategy:** Prevents OOM on the 16 GB primary device by streaming in 5 MB parts. Automatically aborts the upload on exception.

**Public URL pattern:**
```
https://s3.<B2_REGION>.backblazeb2.com/<bucket>/<key>
```

**Storage key pattern for uploads:**
```
uploads/{document_id}/{original_filename}
```

---

## Planned Implementation

```python
# api/routers/documents.py
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".epub"}

@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage),
) -> dict:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, f"Unsupported format: {ext}")

    document_id = str(uuid.uuid4())
    key = f"uploads/{document_id}/{file.filename}"
    url = storage.upload(key, await file.read(), content_type=file.content_type)

    # Persist Document record to DB
    return {"document_id": document_id, "storage_key": key, "size_bytes": ...}
```

---

## Pending Implementation

- [ ] Full `POST /documents/upload` implementation
- [ ] File extension validation returning `422` for unsupported types
- [ ] `Document` DB record creation after successful upload
- [ ] `GET /documents/{id}` — retrieve document metadata
- [ ] Integration with `StorageService` dependency injection

---

## Accepted File Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| PDF | `.pdf` | Docling (default), PDFPlumber, PyPDF, PyMuPDF |
| Word | `.docx` | python-docx, Mammoth |
| eBook | `.epub` | ebooklib, BeautifulSoup |

---

## Acceptance Criteria Status

- [ ] `POST /documents/upload` with a PDF returns `201` and a `document_id`
- [ ] File is visible in B2 bucket under `uploads/{document_id}/`
- [ ] Unsupported formats (`.txt`, `.png`) return `422`
- [ ] Files > 100 MB use multipart upload without memory errors
