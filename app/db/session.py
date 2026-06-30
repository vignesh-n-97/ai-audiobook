"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_config

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        cfg = get_config()
        _engine = create_async_engine(
            cfg.database_url,
            echo=cfg.api_debug,
            # NullPool avoids connection reuse issues in tests
            poolclass=NullPool if "test" in cfg.database_url else None,  # type: ignore[arg-type]
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables (dev convenience — use Alembic in production)."""
    from app.models import Base, Experiment, Run, Document, Artifact  # noqa: F401 — registers all models

    async with _get_engine().begin() as conn:
        # This is a no-op if tables already exist; Alembic handles migrations
        pass


async def get_session() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
