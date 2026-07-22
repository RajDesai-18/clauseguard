"""Shared test fixtures."""

from __future__ import annotations

import os

# Disable OpenTelemetry before any app module is imported. Importing app.main
# runs setup_tracing() at module load, which would otherwise stand up an OTLP
# exporter pointed at the Docker-only `jaeger` hostname. That host is
# unresolvable from the local test environment, so the exporter's background
# thread loops on connection errors and spews tracebacks (including
# shutdown-time "I/O operation on closed file"). Tests have no need to export
# telemetry; turning tracing off keeps the run clean and side-effect free.
# Must be set before the app imports below, since Settings reads the env once
# on first import.
os.environ.setdefault("OTEL_ENABLED", "false")

import logging  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.api.deps import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints (unauthenticated)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await _cleanup_singletons()


@pytest.fixture
def test_user() -> User:
    """In-memory User instance for use as a test fixture.

    Not persisted to the database. Use this when a test only needs the
    user object to satisfy a dependency override; for tests that read
    the user back from the DB, persist it explicitly inside the test.
    """
    now = datetime.now(UTC)
    return User(
        id=str(uuid4()),
        name="Test User",
        email="test@clauseguard.dev",
        email_verified=True,
        image=None,
        plan="free",
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def authenticated_client(test_user: User):
    """Async HTTP client with `get_current_user` overridden to return test_user.

    Use this for tests against endpoints protected by `Depends(get_current_user)`.
    The override is scoped to the fixture and cleaned up automatically so it
    can't leak into other tests.
    """

    async def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup_singletons()


async def _cleanup_singletons() -> None:
    """Reset DB engine and Redis client between tests to avoid event loop leaks."""
    try:
        from app.core.database import dispose_engine

        await dispose_engine()
    except RuntimeError:
        pass

    try:
        from app.core.redis import close_redis

        await close_redis()
    except RuntimeError:
        pass


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
