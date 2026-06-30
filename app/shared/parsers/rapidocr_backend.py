"""RapidOCRParser — AUD-023.

OCR backend for scanned PDFs (image-only, no text layer).

Pipeline:
  1. Rasterise each PDF page to a PNG byte array via PyMuPDF (fitz)
  2. Pass each page image to RapidOCR (ONNX-based, CPU-optimised)
  3. Join detected text lines in reading order
  4. Return as plain markdown (no structure detection at this stage)

Install:
    pip install rapidocr-onnxruntime pymupdf

CPU note: RapidOCR with ONNX is the fastest CPU-compatible OCR option.
At 150 DPI, a 10-page scanned PDF processes in ~10–30 seconds on the
primary device.

See TASKS.md §AUD-023 for full spec and acceptance criteria.
"""

from __future__ import annotations

import structlog

from app.shared.interfaces import Parser, ParseResult

log = structlog.get_logger(__name__)

# Rasterisation resolution — 150 DPI balances speed and OCR accuracy.
# Increase to 200+ DPI for better accuracy on low-quality scans.
_DEFAULT_DPI = 150


class RapidOCRParser(Parser):
    """Scanned PDF parser using RapidOCR (ONNX runtime, CPU-optimised).

    Selectable via: ocr_backend=rapidocr in config.
    Only applicable to scanned (image-only) PDFs — for text-layer PDFs,
    use DoclingParser which is faster and produces richer output.
    """

    def __init__(self, dpi: int = _DEFAULT_DPI) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise ImportError(
                "rapidocr-onnxruntime is not installed. "
                "Run: pip install rapidocr-onnxruntime"
            ) from exc
        try:
            import fitz  # noqa: F401 — verify pymupdf is available at init time
        except ImportError as exc:
            raise ImportError(
                "pymupdf is not installed (needed for rasterisation). "
                "Run: pip install pymupdf"
            ) from exc

        self._engine = RapidOCR()
        self._dpi = dpi

    @property
    def supported_formats(self) -> list[str]:
        return [".pdf"]  # scanned PDFs only

    def parse(self, file_path: str) -> ParseResult:
        """Rasterise and OCR a scanned PDF.

        Args:
            file_path: Absolute path to the scanned PDF.

        Returns:
            ParseResult with OCR text joined by newlines.
            No heading structure is inferred — that is left to downstream
            structural analysis (AUD-030).
        """
        log.info("rapidocr_parser.parse.start", file_path=file_path, dpi=self._dpi)

        pages = self._rasterize(file_path, dpi=self._dpi)
        all_lines: list[str] = []

        for page_idx, page_bytes in enumerate(pages):
            try:
                result, _ = self._engine(page_bytes)
            except Exception as exc:
                log.warning(
                    "rapidocr_parser.page_failed",
                    page=page_idx,
                    error=str(exc),
                )
                continue

            if result:
                # result is a list of [bbox, text, confidence]
                all_lines.extend(item[1] for item in result if item[1])

        markdown = "\n".join(all_lines)

        log.info(
            "rapidocr_parser.parse.complete",
            file_path=file_path,
            page_count=len(pages),
            line_count=len(all_lines),
            char_count=len(markdown),
        )

        return ParseResult(
            markdown=markdown,
            metadata={
                "page_count": len(pages),
                "line_count": len(all_lines),
                "dpi": self._dpi,
            },
            source_path=file_path,
            parser_name="rapidocr",
        )

    @staticmethod
    def _rasterize(path: str, dpi: int = _DEFAULT_DPI) -> list[bytes]:
        """Convert each PDF page to a PNG byte array.

        Uses PyMuPDF (fitz) solely for rasterisation — not for text extraction.
        Returns a list of PNG byte strings, one per page.
        """
        import fitz

        doc = fitz.open(path)
        pages: list[bytes] = []
        for page in doc:
            pixmap = page.get_pixmap(dpi=dpi)
            pages.append(pixmap.tobytes("png"))
        doc.close()
        return pages
