"""Fixtures for saga task tests.

These tests run against a real Postgres (and skip cleanly when
Postgres isn't reachable). LLM and embedding calls are mocked at
the service layer; database writes are real and rolled back at
teardown. Celery is configured to run tasks eagerly so we can
assert on results without a worker.
"""

from __future__ import annotations

import socket
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.core.config import settings
from app.models.contract import Contract
from app.models.user import User


def _postgres_reachable() -> bool:
    """Return True if Postgres is reachable on localhost:5432."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 5432))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


# Skip every test in this module if Postgres isn't reachable. Saga tests
# can't run without a real DB; we don't pretend otherwise with extra mocking.
pytestmark = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="PostgreSQL not reachable on localhost:5432",
)


@pytest.fixture(scope="session", autouse=True)
def celery_eager_mode():
    """Run all Celery tasks synchronously in-process for the test session.

    With task_always_eager=True, calling task.delay() or task.apply_async()
    runs the task immediately and returns a finished AsyncResult.
    task_eager_propagates=True makes exceptions in tasks raise normally
    instead of being wrapped in the AsyncResult.
    """
    original_eager = celery_app.conf.task_always_eager
    original_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = original_eager
    celery_app.conf.task_eager_propagates = original_propagates


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    """Sync DB session for test setup and assertions.

    Mirrors the pattern in app/tasks/_session.py. Each test gets a
    fresh session; the engine is disposed at teardown so the next
    test starts clean.
    """
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url, future=True)
    session_factory = sessionmaker(bind=engine, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def db_user(sync_session: Session) -> Generator[User, None, None]:
    """Persisted test user for FK dependencies, cleaned up after the test."""
    now = datetime.now(UTC)
    user = User(
        id=str(uuid4()),
        name="Saga Test User",
        email=f"saga-{uuid4().hex[:8]}@clauseguard.test",
        email_verified=True,
        image=None,
        plan="free",
        created_at=now,
        updated_at=now,
    )
    sync_session.add(user)
    sync_session.commit()
    user_id = user.id
    yield user
    # Cleanup. Use a fresh session bound to the same engine so we're not
    # affected by any connection-level state changes the saga tasks made
    # in their own sessions during the test. Cascade delete handles any
    # contracts and clauses created during the test.
    sync_session.rollback()  # discard any uncommitted state from the test
    fresh = sync_session.get(User, user_id)
    if fresh is not None:
        sync_session.delete(fresh)
        sync_session.commit()


@pytest.fixture
def db_contract(sync_session: Session, db_user: User) -> Contract:
    """Persisted test contract in 'parsed' state with raw_text populated.

    Most saga tests start downstream of the parse step. Tests for
    parse_document_task itself should build a contract without raw_text.
    """
    contract = Contract(
        id=uuid4(),
        user_id=db_user.id,
        file_name="test_contract.pdf",
        file_url=f"test/{uuid4()}.pdf",
        file_hash=uuid4().hex,
        status="parsed",
        raw_text=(
            "1. Confidentiality. Each party agrees to maintain confidentiality "
            "of all proprietary information.\n\n"
            "2. Term. This agreement shall remain in effect for two years."
        ),
    )
    sync_session.add(contract)
    sync_session.commit()
    sync_session.refresh(contract)
    return contract


@pytest.fixture
def fake_split_response() -> dict:
    """Canned response from the clause splitter LLM."""
    return {
        "contract_type": "nda",
        "summary": "A short test NDA.",
        "clauses": [
            {
                "clause_type": "confidentiality",
                "original_text": (
                    "Each party agrees to maintain confidentiality of all proprietary information."
                ),
                "position": 1,
            },
            {
                "clause_type": "termination",
                "original_text": "This agreement shall remain in effect for two years.",
                "position": 2,
            },
        ],
    }


@pytest.fixture
def fake_analysis_yellow() -> dict:
    """Canned analyzer response for a yellow-risk clause."""
    return {
        "risk_level": "yellow",
        "confidence": 0.85,
        "explanation": "This clause is somewhat one-sided.",
        "market_comparison": "Standard clauses are more balanced.",
    }


@pytest.fixture
def fake_analysis_green() -> dict:
    """Canned analyzer response for a green-risk clause."""
    return {
        "risk_level": "green",
        "confidence": 0.95,
        "explanation": "Standard, market-typical language.",
        "market_comparison": "Matches common NDA templates.",
    }
