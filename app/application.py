"""
FastAPI application factory.

Responsibilities of app/api (per AGENTS.md):
  - authentication
  - user management
  - project management
  - experiment management
  - artifact management
  - orchestration APIs

Must NOT contain business logic — that lives in app/shared/.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_config
from app.db.session import init_db
from app.middleware.logging import LoggingMiddleware
from app.middleware.tracing import configure_tracing
from app.shared.logging import configure_logging

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Startup service connectivity checks
# ---------------------------------------------------------------------------


async def _check_database(cfg) -> None:
    """Verify DB is reachable at startup. Logs a warning if not — never raises."""
    try:
        from sqlalchemy import text

        from app.db.session import _get_session_factory
        factory = _get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        log.info("startup.db_connected", url=cfg.database_url.split("@")[-1])
    except Exception as exc:
        log.warning(
            "startup.db_unreachable",
            url=cfg.database_url.split("@")[-1],
            error=str(exc),
            hint=(
                "Ensure PostgreSQL is running: docker compose up -d postgres. "
                "API will start but DB-dependent routes will fail until connected."
            ),
        )


async def _check_redis(cfg) -> None:
    """Verify Redis is reachable at startup. Logs a warning if not — never raises."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(cfg.redis_url)
        await r.ping()
        await r.aclose()
        log.info("startup.redis_connected", url=cfg.redis_url)
    except Exception as exc:
        log.warning(
            "startup.redis_unreachable",
            url=cfg.redis_url,
            error=str(exc),
            hint=(
                "Ensure Redis is running: docker compose up -d redis. "
                "Celery task dispatch will fail until Redis is available."
            ),
        )


async def _check_mlflow(cfg) -> None:
    """Verify MLflow tracking server is reachable at startup. Logs a warning if not."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{cfg.mlflow_tracking_uri}/health")
            resp.raise_for_status()
        log.info("startup.mlflow_connected", uri=cfg.mlflow_tracking_uri)
    except Exception as exc:
        log.warning(
            "startup.mlflow_unreachable",
            uri=cfg.mlflow_tracking_uri,
            error=str(exc),
            hint=(
                "Ensure MLflow is running: docker compose up -d mlflow. "
                "RunTracker.start_run() will fail until MLflow is available. "
                "Pipeline runs cannot be tracked without a live MLflow server."
            ),
        )


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown.

    Connectivity checks are non-blocking — a missing service is warned but
    never prevents the API from starting. This allows partial operation
    (e.g. document upload) even when MLflow or Redis is temporarily down.
    """
    cfg = get_config()
    configure_logging(level="DEBUG" if cfg.api_debug else "INFO")
    configure_tracing(cfg)
    await init_db()

    # Non-blocking connectivity checks — log warnings for any unreachable services
    await _check_database(cfg)
    await _check_redis(cfg)
    await _check_mlflow(cfg)

    log.info("api.started", version=app.version, git_sha=cfg.git_sha)
    yield
    log.info("api.shutdown")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def get_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = get_config()

    app = FastAPI(
        title="AI Audiobook Platform API",
        description=(
            "Orchestration API for the AI Audiobook experimentation platform. "
            "Manages documents, experiments, runs, and artifacts."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if cfg.api_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured request logging
    app.add_middleware(LoggingMiddleware)

    # All routes via aggregated router
    app.include_router(router)

    return app


# ASGI entrypoint used by uvicorn
app = get_app()
