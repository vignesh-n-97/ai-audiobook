"""TxtParser — plain text passthrough parser.

No extraction needed: reads the file as UTF-8 and returns it as-is.
This is the simplest possible parser — useful for pre-formatted text manuscripts.
"""

from __future__ import annotations

from app.shared.interfaces import Parser, ParseResult


class TxtParser(Parser):
    """Plain-text parser — reads the file directly without any transformation."""

    @property
    def supported_formats(self) -> list[str]:
        return [".txt"]

    def parse(self, file_path: str) -> ParseResult:
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        return ParseResult(
            markdown=content,
            metadata={"char_count": len(content)},
            source_path=file_path,
            parser_name="txt",
        )
