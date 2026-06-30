"""Re-export shim — Base lives in app.models.base; imported here for Alembic compatibility."""

from app.models.base import Base  # noqa: F401

__all__ = ["Base"]
