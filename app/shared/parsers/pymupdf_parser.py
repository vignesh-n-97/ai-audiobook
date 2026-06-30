"""PyMuPDFParser — stub (AUD-021).

AGPL licensed — for internal use only. Do not redistribute.
See TASKS.md §AUD-021 for implementation spec.
Install: pip install pymupdf
"""

from __future__ import annotations

from app.shared.interfaces import Parser, ParseResult


class PyMuPDFParser(Parser):
    @property
    def supported_formats(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> ParseResult:
        raise NotImplementedError(
            "PyMuPDFParser is not yet implemented. "
            "See TASKS.md §AUD-021. Set pdf_parser=docling in config to use the default parser."
        )
