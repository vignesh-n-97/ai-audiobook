"""Parser factory and implementations — AUD-021.

All parser classes live in app/shared/ so both the API and Worker can use them
without violating the layered architecture rules in AGENTS.md.

Usage:
    from app.shared.parsers.factory import get_parser
    parser = get_parser(cfg, ".pdf")
    result: ParseResult = parser.parse("/path/to/doc.pdf")
"""
