"""Tests for pgvector semantic clause caching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import semantic_cache as cache_module
from app.services.semantic_cache import SIMILARITY_THRESHOLD, find_similar_clause


def _make_db_row(
    clause_type: str = "indemnification",
    risk_level: str = "yellow",
    confidence: float = 0.85,
    explanation: str = "Some explanation.",
    market_comparison: str = "Standard comparison.",
    similarity: float = 0.95,
) -> MagicMock:
    """Build a mock SQLAlchemy row result."""
    row = MagicMock()
    row.clause_type = clause_type
    row.risk_level = risk_level
    row.confidence = confidence
    row.explanation = explanation
    row.market_comparison = market_comparison
    row.similarity = similarity
    return row


@pytest.fixture
def mock_session():
    """Provide a mock session and patch _get_sync_session to return it."""
    session = MagicMock()
    with patch.object(cache_module, "_get_sync_session", return_value=session):
        yield session


@pytest.fixture(autouse=True)
def mock_embedding():
    """Stub out embedding generation to avoid hitting OpenAI."""
    fake_vector = [0.1] * 1536
    with patch.object(cache_module, "generate_embedding", return_value=fake_vector) as m:
        yield m


def test_cache_hit_above_threshold_returns_analysis(mock_session):
    """A similarity score >= threshold should return the cached analysis."""
    row = _make_db_row(similarity=0.95)
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_similar_clause("some clause text")

    assert result is not None
    assert result["risk_level"] == "yellow"
    assert result["confidence"] == 0.85
    assert result["explanation"] == "Some explanation."
    assert result["market_comparison"] == "Standard comparison."


def test_cache_hit_exactly_at_threshold_returns_analysis(mock_session):
    """Similarity exactly at threshold should count as a hit."""
    row = _make_db_row(similarity=SIMILARITY_THRESHOLD)
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_similar_clause("some clause text")

    assert result is not None
    assert result["risk_level"] == "yellow"


def test_cache_miss_below_threshold_returns_none(mock_session):
    """A similarity score below threshold should return None."""
    row = _make_db_row(similarity=0.80)
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_similar_clause("some clause text")

    assert result is None


def test_no_existing_clauses_returns_none(mock_session):
    """When no rows exist, fetchone returns None and we should return None."""
    mock_session.execute.return_value.fetchone.return_value = None

    result = find_similar_clause("some clause text")

    assert result is None


def test_exception_during_search_returns_none_gracefully(mock_session):
    """Any DB exception should be swallowed and return None (graceful degradation)."""
    mock_session.execute.side_effect = RuntimeError("pgvector blew up")

    result = find_similar_clause("some clause text")

    assert result is None


def test_embedding_failure_returns_none_gracefully():
    """If embedding generation fails, we should degrade gracefully."""
    session = MagicMock()
    with (
        patch.object(cache_module, "_get_sync_session", return_value=session),
        patch.object(cache_module, "generate_embedding", side_effect=RuntimeError("openai down")),
    ):
        result = find_similar_clause("some clause text")

    assert result is None


def test_session_is_always_closed(mock_session):
    """The session should be closed even when an exception occurs."""
    mock_session.execute.side_effect = RuntimeError("boom")

    find_similar_clause("some clause text")

    mock_session.close.assert_called_once()


def test_session_closed_on_cache_hit(mock_session):
    """The session should be closed on the happy path too."""
    row = _make_db_row(similarity=0.95)
    mock_session.execute.return_value.fetchone.return_value = row

    find_similar_clause("some clause text")

    mock_session.close.assert_called_once()


def test_confidence_none_defaults_to_zero(mock_session):
    """A NULL confidence in the DB should normalize to 0.0, not crash."""
    row = _make_db_row(confidence=None, similarity=0.95)  # type: ignore
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_similar_clause("some clause text")

    assert result is not None
    assert result["confidence"] == 0.0


def test_embedding_is_generated_from_input_text(mock_session, mock_embedding):
    """The embedding function should be called with the exact input text."""
    row = _make_db_row(similarity=0.95)
    mock_session.execute.return_value.fetchone.return_value = row

    find_similar_clause("very specific clause text")

    mock_embedding.assert_called_once_with("very specific clause text")
