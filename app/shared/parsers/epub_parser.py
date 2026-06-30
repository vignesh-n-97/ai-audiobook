"""EpubParser — stub (AUD-021).

Default backend uses ebooklib (AGPL — internal use only).
Alternative: BSEpubParser using beautifulsoup4 (MIT).
See TASKS.md §AUD-021 for implementation spec.
Install: pip install ebooklib
"""

from __future__ import annotations

from app.shared.interfaces import Parser, ParseResult


class EpubParser(Parser):
    @property
    def supported_formats(self) -> list[str]:
        return [".epub"]

    def parse(self, file_path: str) -> ParseResult:
        raise NotImplementedError(
            "EpubParser is not yet implemented. "
            "See TASKS.md §AUD-021."
        )
