"""DoclingParser — AUD-022.

Uses IBM Docling to convert PDFs, DOCX, and EPUB files into structured markdown,
preserving headings, tables, and reading order.

Docling's internal OCR pipeline is configurable via the `ocr_backend` config key.
This means you do not need a separate RapidOCRParser for scanned PDFs — Docling
handles OCR internally and also preserves document structure:

    ocr_backend=rapidocr  → Docling uses RapidOCR-ONNX (default, CPU-optimised)
    ocr_backend=easyocr   → Docling uses EasyOCR
    ocr_backend=tesseract → Docling uses Tesseract

Install: pip install docling
First run downloads ~500 MB of layout models to ~/.cache/docling (one-time).

CPU note: On the primary 16 GB device, a 300-page PDF takes ~2–4 minutes.
This is acceptable for an experiment platform where quality > speed.

See TASKS.md §AUD-022 for full spec and acceptance criteria.
"""

from __future__ import annotations

import contextlib

import structlog

from app.shared.config import Config
from app.shared.interfaces import Parser, ParseResult

log = structlog.get_logger(__name__)


class DoclingParser(Parser):
    """Multi-format parser using IBM Docling — the default backend for PDF, DOCX, and EPUB.

    Produces structured markdown with:
      - Headings preserved as #, ##, ###
      - Tables rendered as markdown tables
      - Reading order respected for multi-column layouts
      - OCR applied to scanned pages using the configured ocr_backend

    The ``ocr_backend`` config key controls which OCR engine Docling uses
    internally (rapidocr | easyocr | tesseract). RapidOCR is the default
    and best suited for CPU-only hardware.

    The DocumentConverter is instantiated once per parser instance and reused
    across calls. Docling loads its layout models lazily on first conversion.
    """

    def __init__(self, cfg: Config | None = None) -> None:
        """Initialise DoclingParser, optionally configuring the OCR backend.

        Args:
            cfg: Platform config. If provided, the ``ocr_backend`` key is used
                 to configure Docling's internal OCR pipeline. If None, Docling
                 uses its built-in default (RapidOCR).
        """
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as exc:
            raise ImportError(
                "docling is not installed. Run: pip install docling"
            ) from exc

        if cfg is not None:
            pipeline_options = self._build_pipeline_options(cfg)
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
                }
            )
        else:
            # Default: Docling uses RapidOCR internally
            self._converter = DocumentConverter()

    @property
    def supported_formats(self) -> list[str]:
        """Docling natively handles PDF, DOCX, and EPUB."""
        return [".pdf", ".docx", ".epub"]

    def parse(self, file_path: str) -> ParseResult:
        """Convert a document at *file_path* to structured markdown.

        Docling auto-detects the file format and applies the appropriate
        pipeline (PDF layout model, DOCX style extraction, EPUB parsing).
        For scanned PDF pages, the configured OCR engine is applied automatically.

        Args:
            file_path: Absolute path to the document file.

        Returns:
            ParseResult with full markdown content and metadata.
        """
        log.info("docling_parser.parse.start", file_path=file_path)

        result = self._converter.convert(file_path)
        doc = result.document
        markdown = doc.export_to_markdown()

        # page_count: available on PDF documents; not meaningful for DOCX/EPUB
        page_count: int | None = None
        with contextlib.suppress(AttributeError, TypeError):
            page_count = len(doc.pages)

        # title: present on some documents
        title: str | None = None
        with contextlib.suppress(AttributeError):
            title = doc.name or None

        log.info(
            "docling_parser.parse.complete",
            file_path=file_path,
            page_count=page_count,
            markdown_chars=len(markdown),
        )

        return ParseResult(
            markdown=markdown,
            metadata={
                "page_count": page_count,
                "title": title,
            },
            source_path=file_path,
            parser_name="docling",
        )

    @staticmethod
    def _build_pipeline_options(cfg: Config):
        """Build Docling PDF pipeline options from the platform config.

        Maps ``cfg.ocr_backend`` to the appropriate Docling OCR options class.
        Non-PDF formats (DOCX, EPUB) use their own Docling pipelines automatically
        and are not affected by these PDF-specific options.
        """
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        pipeline_options = PdfPipelineOptions()

        match cfg.ocr_backend:
            case "rapidocr":
                from docling.datamodel.pipeline_options import RapidOcrOptions
                pipeline_options.ocr_options = RapidOcrOptions()
                log.debug("docling_parser.ocr_backend", backend="rapidocr")

            case "easyocr":
                try:
                    from docling.datamodel.pipeline_options import EasyOcrOptions
                    pipeline_options.ocr_options = EasyOcrOptions()
                    log.debug("docling_parser.ocr_backend", backend="easyocr")
                except ImportError:
                    log.warning(
                        "docling_parser.easyocr_unavailable",
                        fallback="rapidocr",
                    )
                    from docling.datamodel.pipeline_options import RapidOcrOptions
                    pipeline_options.ocr_options = RapidOcrOptions()

            case "tesseract":
                try:
                    from docling.datamodel.pipeline_options import TesseractOcrOptions
                    pipeline_options.ocr_options = TesseractOcrOptions()
                    log.debug("docling_parser.ocr_backend", backend="tesseract")
                except ImportError:
                    log.warning(
                        "docling_parser.tesseract_unavailable",
                        fallback="rapidocr",
                    )
                    from docling.datamodel.pipeline_options import RapidOcrOptions
                    pipeline_options.ocr_options = RapidOcrOptions()

            case _:
                # paddleocr and any future backends — fall back to rapidocr within Docling
                log.warning(
                    "docling_parser.unknown_ocr_backend",
                    backend=cfg.ocr_backend,
                    fallback="rapidocr",
                )
                from docling.datamodel.pipeline_options import RapidOcrOptions
                pipeline_options.ocr_options = RapidOcrOptions()

        return pipeline_options
