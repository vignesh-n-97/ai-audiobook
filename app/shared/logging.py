"""
Structured logging configuration using structlog.

All logs are emitted as JSON to stdout. Every log event should include
enough context to answer: What happened? When? Which experiment? Which run?

Usage:
    from app.shared.logging import get_logger
    log = get_logger(__name__)
    log.info("document.parsed", parser="docling", page_count=42, run_id="abc")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


class NamedPrintLoggerFactory:
    """Factory that returns PrintLogger instances with a 'name' attribute.

    This works around structlog.stdlib.add_logger_name processor expecting
    logger.name, which standard PrintLogger does not have.
    """

    def __init__(self, file: Any = None) -> None:
        self.file = file or sys.stdout

    def __call__(self, *args: Any, **kwargs: Any) -> structlog.PrintLogger:
        name = args[0] if args else "root"
        logger = structlog.PrintLogger(self.file)
        setattr(logger, "name", name)
        return logger


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog for the process.

    Call once at application startup (main.py / worker entrypoint).
    Subsequent calls to get_logger() will use this configuration.
    """
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        context_class=dict,
        logger_factory=NamedPrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for *name*.

    Example:
        log = get_logger(__name__)
        log.info("tts.synthesized", voice="af_bella", duration_s=3.2)
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
