"""Shared test fixtures."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    eng = create_async_engine(settings.database_url, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine):
    """Create a fresh DB session per test with transaction rollback."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await trans.rollback()


@pytest.fixture
async def client(db_session):
    """Async HTTP client that uses the test DB session."""
    from app.api.deps import get_db
    from app.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
