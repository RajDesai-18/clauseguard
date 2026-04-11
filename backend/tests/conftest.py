"""Shared test fixtures."""

import logging

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    from app.core.database import dispose_engine
    from app.core.redis import close_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Reset singletons so the next test gets a fresh engine on its own loop
    await dispose_engine()
    await close_redis()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "db: mark test as requiring a live database")


def pytest_collection_modifyitems(config, items):
    """Auto-skip @pytest.mark.db tests when postgres is not reachable."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 5432))
        sock.close()
        return
    except (ConnectionRefusedError, OSError):
        pass

    skip_no_db = pytest.mark.skip(reason="PostgreSQL not reachable on localhost:5432")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip_no_db)