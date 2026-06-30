"""API smoke tests."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.application import get_app


@pytest.fixture
def app():
    return get_app()


@pytest.mark.asyncio
async def test_health_returns_200(app):
    """GET /health should return 200 even when DB/Redis are unavailable in CI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    # In CI without DB we still expect the endpoint to respond
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "version" in body


@pytest.mark.asyncio
async def test_documents_stub(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/documents")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_experiments_stub(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/experiments")
    assert resp.status_code == 200
