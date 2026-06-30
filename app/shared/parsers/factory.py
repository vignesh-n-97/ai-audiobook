"""Parser factory — AUD-021.

Returns the correct Parser implementation for a given file format and config.

Swapping parsers requires only a config change — no business logic changes.
Unimplemented backends raise NotImplementedError with the relevant ticket
reference so the failure is clearly actionable.

Default routing:
    .pdf   → DoclingParser  (config: pdf_parser = docling | pdfplumber | pypdf | pymupdf)
    .docx  → DoclingParser  (Docling natively handles DOCX with style/structure extraction)
    .epub  → DoclingParser  (Docling natively handles EPUB2/EPUB3)
    .txt   → TxtParser      (plain passthrough)

OCR backend (for scanned content within PDFs):
    ocr_backend = rapidocr (default) | easyocr | tesseract

Docling handles OCR internally — the ``ocr_backend`` config key routes to
Docling's built-in OCR options (RapidOcrOptions, EasyOcrOptions, etc.).
The standalone RapidOCRParser is kept as an alternative for cases where Docling's
layout model is unnecessary (e.g. bulk plain-text OCR benchmarks).

See TASKS.md §AUD-021 for the full alternatives table.
"""

from __future__ import annotations

from app.shared.config import Config
from app.shared.interfaces import Parser


def get_parser(cfg: Config, file_format: str) -> Parser:
    """Return the configured Parser for *file_format*.

    Args:
        cfg:         Platform config (reads pdf_parser / ocr_backend keys).
        file_format: File extension including dot, e.g. '.pdf', '.docx', '.epub'.

    Raises:
        ValueError:          No parser is registered for the given format.
        NotImplementedError: Parser is registered but not yet implemented.
    """
    ext = file_format.lower()

    if ext == ".pdf":
        match cfg.pdf_parser:
            case "docling":
                from .docling_parser import DoclingParser
                return DoclingParser(cfg=cfg)
            case "pdfplumber":
                from .pdfplumber_parser import PDFPlumberParser
                return PDFPlumberParser()
            case "pypdf":
                from .pypdf_parser import PyPDFParser
                return PyPDFParser()
            case "pymupdf":
                from .pymupdf_parser import PyMuPDFParser
                return PyMuPDFParser()
            case _:
                raise ValueError(
                    f"Unknown pdf_parser {cfg.pdf_parser!r}. "
                    "Valid values: docling | pdfplumber | pypdf | pymupdf"
                )

    if ext == ".docx":
        # Docling is the default for DOCX — it preserves styles, headings, and tables.
        # Specific alternatives (python-docx, mammoth) remain as stubs (AUD-021).
        from .docling_parser import DoclingParser
        return DoclingParser(cfg=cfg)

    if ext == ".epub":
        # Docling handles EPUB2/EPUB3 natively.
        # Alternatives (ebooklib, beautifulsoup4) remain as stubs (AUD-021).
        from .docling_parser import DoclingParser
        return DoclingParser(cfg=cfg)

    if ext == ".txt":
        from .txt_parser import TxtParser
        return TxtParser()

    raise ValueError(
        f"No parser registered for format {ext!r}. "
        "Supported: .pdf | .docx | .epub | .txt"
    )


def get_ocr_parser(cfg: Config) -> Parser:
    """Return a standalone OCR parser for scanned PDFs.

    Prefer using DoclingParser (via get_parser) which handles OCR internally
    while also preserving document structure. Use this only when Docling's
    layout model is not needed (e.g. plain bulk OCR benchmarks).
    """
    match cfg.ocr_backend:
        case "rapidocr":
            from .rapidocr_backend import RapidOCRParser
            return RapidOCRParser()
        case "easyocr" | "paddleocr" | "tesseract":
            raise NotImplementedError(
                f"Standalone OCR backend {cfg.ocr_backend!r} is not yet implemented. "
                "For OCR within Docling, set pdf_parser=docling — Docling uses "
                f"the configured ocr_backend={cfg.ocr_backend!r} internally."
            )
        case _:
            raise ValueError(
                f"Unknown ocr_backend {cfg.ocr_backend!r}. "
                "Valid values: rapidocr | easyocr | paddleocr | tesseract"
            )
