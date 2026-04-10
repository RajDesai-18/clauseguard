"""Shared test fixtures."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SKIP_DB_TESTS = sys.platform == "win32"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
