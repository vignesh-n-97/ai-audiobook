"""DocxParser — stub (AUD-021).

See TASKS.md §AUD-021 for implementation spec.
Install: pip install python-docx
"""

from __future__ import annotations

from app.shared.interfaces import Parser, ParseResult


class DocxParser(Parser):
    @property
    def supported_formats(self) -> list[str]:
        return [".docx"]

    def parse(self, file_path: str) -> ParseResult:
        raise NotImplementedError(
            "DocxParser is not yet implemented. "
            "See TASKS.md §AUD-021."
        )
