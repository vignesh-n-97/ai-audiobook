"""Aggregated API router — includes all route modules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers import health, documents, experiments

router = APIRouter()

router.include_router(health.router)
router.include_router(documents.router, prefix="/documents")
router.include_router(experiments.router, prefix="/experiments")
