"""Health check router.

GET /health — returns service health and connectivity status.
Response includes git_sha for version traceability (AUD-003).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.db.session import get_session

router = APIRouter(tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/health", summary="Health check")
async def health(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return service health.

    Checks:
      - DB connectivity (SELECT 1)
      - Redis connectivity (ping)

    Returns git_sha from GIT_SHA env var for version traceability.
    """
    cfg = get_config()
    db_status = "unknown"
    redis_status = "unknown"

    # Database check
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        log.warning("health.db_check_failed", error=str(exc))
        db_status = "error"

    # Redis check
    try:
        import redis.asyncio as aioredis  # lazy import — only here

        r = aioredis.from_url(cfg.redis_url)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception as exc:
        log.warning("health.redis_check_failed", error=str(exc))
        redis_status = "error"

    return {
        "status": "healthy",
        "db": db_status,
        "redis": redis_status,
        "version": cfg.git_sha,
    }
