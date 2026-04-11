"""Shared test fixtures."""

import asyncio
import logging

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def db_available():
    """Check if PostgreSQL is reachable. Used to skip DB tests locally."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 5432))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


needs_db = pytest.mark.skipif(
    "not config.getoption('--force-db', default=False)",
    reason="Skipped: PostgreSQL not guaranteed locally. Runs in CI.",
)


def pytest_configure(config):
    """Register custom markers and options."""
    config.addinivalue_line("markers", "db: mark test as requiring a live database")


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests that hit the database when postgres is not reachable."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 5432))
        sock.close()
        pg_up = True
    except (ConnectionRefusedError, OSError):
        pg_up = False

    if pg_up:
        return

    skip_no_db = pytest.mark.skip(reason="PostgreSQL not reachable on localhost:5432")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip_no_db)