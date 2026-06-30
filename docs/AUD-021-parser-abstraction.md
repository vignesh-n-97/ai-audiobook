# AUD-021 — Parser Abstraction Layer

**Epic:** EPIC 3 — Document Ingestion  
**Status:** 🔲 Interface defined; factory pending  
**Priority:** High  
**Depends on:** AUD-020  
**Blocks:** AUD-022, AUD-023  

---

## Summary

Provides a factory function `get_parser(cfg, file_format)` that returns the correct `Parser` implementation based on the `pdf_parser`, `ocr_backend`, etc. config keys. Adding a new parser never requires changes to business logic — only to the factory and a new implementation file.

---

## What Was Implemented

### `Parser` ABC (`shared/interfaces.py`)

```python
class Parser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParseResult: ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]: ...
```

### `ParseResult` dataclass

```python
@dataclass
class ParseResult:
    markdown: str
    metadata: dict[str, Any]
    source_path: str
    parser_name: str      # logged as MLflow param on every run
```

---

## Planned Factory (`api/parsers/factory.py`)

```python
def get_parser(cfg: Config, file_format: str) -> Parser:
    if file_format == ".pdf":
        match cfg.pdf_parser:
            case "docling":    return DoclingParser()
            case "pdfplumber": return PDFPlumberParser()
            case "pypdf":      return PyPDFParser()
            case "pymupdf":    return PyMuPDFParser()
    elif file_format == ".docx":
        return DocxParser()
    elif file_format == ".epub":
        return EpubParser()
    raise ValueError(f"No parser for format: {file_format}")
```

---

## Parser Alternatives Reference

### PDF Parsers

| Implementation | Package | License | When to prefer |
|---------------|---------|---------|----------------|
| `DoclingParser` (default) | `docling` | MIT | Structured markdown with headings, tables |
| `PDFPlumberParser` | `pdfplumber` | MIT | Text + table extraction without LLM |
| `PyPDFParser` | `pypdf` | MIT | Lightweight; basic text only |
| `PyMuPDFParser` | `pymupdf` | AGPL | Fastest; richest; internal use only |

### OCR Backends (for scanned PDFs)

| Implementation | Package | License | When to prefer |
|---------------|---------|---------|----------------|
| `RapidOCRBackend` (default) | `rapidocr-onnxruntime` | Apache 2.0 | CPU-optimised ONNX |
| `EasyOCRBackend` | `easyocr` | Apache 2.0 | Better on degraded/skewed scans |
| `PaddleOCRBackend` | `paddleocr` | Apache 2.0 | Best accuracy; heavier |
| `TesseractBackend` | `pytesseract` | Apache 2.0 | Lightest; weakest on complex layouts |

### DOCX Parsers

| Implementation | Package | License | When to prefer |
|---------------|---------|---------|----------------|
| `DocxParser` (default) | `python-docx` | MIT | Full style/structure access |
| `MammothParser` | `mammoth` | MIT | Better semantic HTML output |

### EPUB Parsers

| Implementation | Package | License | When to prefer |
|---------------|---------|---------|----------------|
| `EpubParser` (default) | `ebooklib` | AGPL | Mature EPUB2/EPUB3 (internal only) |
| `BSEpubParser` | `beautifulsoup4` | MIT | Raw HTML parsing; more control |

---

## Pending Implementation

- [ ] `api/parsers/factory.py` — factory function
- [ ] Parser implementations: `DoclingParser`, `PDFPlumberParser`, `PyPDFParser`, `PyMuPDFParser`
- [ ] Parser implementations: `DocxParser`, `EpubParser`
- [ ] OCR backends: `RapidOCRBackend`, `EasyOCRBackend`, `TesseractBackend`
- [ ] `ParseResult.parser_name` logged as MLflow param in pipeline task

---

## Acceptance Criteria Status

- [ ] Changing `PDF_PARSER` in `.env` switches implementation without code changes
- [ ] All parser implementations return a `ParseResult` with valid markdown
- [ ] `ParseResult.parser_name` is logged as an MLflow param on every run
