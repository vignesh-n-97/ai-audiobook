"""PyPDFParser — stub (AUD-021).

See TASKS.md §AUD-021 for implementation spec.
Install: pip install pypdf
"""

from __future__ import annotations

from app.shared.interfaces import Parser, ParseResult


class PyPDFParser(Parser):
    @property
    def supported_formats(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> ParseResult:
        raise NotImplementedError(
            "PyPDFParser is not yet implemented. "
            "See TASKS.md §AUD-021. Set pdf_parser=docling in config to use the default parser."
        )
