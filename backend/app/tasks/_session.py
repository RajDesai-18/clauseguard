"""Shared synchronous DB session factory for Celery tasks.

Celery tasks run in worker processes that don't play nicely with
async SQLAlchemy. This module provides a single sync engine and a
session factory that all tasks should use instead of building their
own engines per call.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_sync_engine() -> Engine:
    """Build the sync engine from the async DATABASE_URL.

    The app uses asyncpg for FastAPI; Celery needs psycopg2.
    We rewrite the driver portion of the URL.
    """
    sync_url = settings.database_url.replace(
        "postgresql+asyncpg",
        "postgresql+psycopg2",
    )
    return create_engine(
        sync_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


_engine: Engine = _build_sync_engine()
_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def get_sync_session() -> Session:
    """Return a new synchronous DB session bound to the shared engine.

    Caller is responsible for closing the session (use try/finally
    or a context manager).
    """
    return _SessionFactory()
