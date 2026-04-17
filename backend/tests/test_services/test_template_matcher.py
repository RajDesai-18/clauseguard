"""Tests for pgvector template matching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import template_matcher as matcher_module
from app.services.template_matcher import find_nearest_template


def _make_template_row(
    clause_type: str = "indemnification",
    standard_text: str = "The standard clause text.",
    source: str | None = "internal",
    similarity: float = 0.88,
) -> MagicMock:
    """Build a mock SQLAlchemy row result."""
    row = MagicMock()
    row.clause_type = clause_type
    row.standard_text = standard_text
    row.source = source
    row.similarity = similarity
    return row


@pytest.fixture
def mock_session():
    """Provide a mock session and patch _get_sync_session to return it."""
    session = MagicMock()
    with patch.object(matcher_module, "_get_sync_session", return_value=session):
        yield session


@pytest.fixture(autouse=True)
def mock_embedding():
    """Stub out embedding generation to avoid hitting OpenAI."""
    fake_vector = [0.1] * 1536
    with patch.object(matcher_module, "generate_embedding", return_value=fake_vector) as m:
        yield m


def test_find_with_contract_type_filter_returns_match(mock_session):
    """A match with contract_type filter should return the template dict."""
    row = _make_template_row(
        clause_type="termination",
        standard_text="Standard termination text.",
        source="lawinsider",
        similarity=0.91,
    )
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_nearest_template("some clause", contract_type="nda")

    assert result is not None
    assert result["clause_type"] == "termination"
    assert result["standard_text"] == "Standard termination text."
    assert result["source"] == "lawinsider"
    assert result["similarity"] == pytest.approx(0.91)


def test_find_without_contract_type_filter_returns_match(mock_session):
    """A match without filter should still return the template dict."""
    row = _make_template_row(similarity=0.75)
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_nearest_template("some clause")

    assert result is not None
    assert result["similarity"] == pytest.approx(0.75)


def test_contract_type_filter_is_passed_to_query(mock_session):
    """The contract_type value should be bound to the SQL query."""
    row = _make_template_row()
    mock_session.execute.return_value.fetchone.return_value = row

    find_nearest_template("some clause", contract_type="msa")

    # Second positional arg to execute() is the params dict
    call_args = mock_session.execute.call_args
    params = call_args.args[1]
    assert params["contract_type"] == "msa"
    assert "embedding" in params


def test_no_contract_type_means_no_filter_in_params(mock_session):
    """Without contract_type, only the embedding param should be bound."""
    row = _make_template_row()
    mock_session.execute.return_value.fetchone.return_value = row

    find_nearest_template("some clause")

    call_args = mock_session.execute.call_args
    params = call_args.args[1]
    assert "contract_type" not in params
    assert "embedding" in params


def test_no_templates_returns_none(mock_session):
    """When no rows exist, fetchone returns None and we should return None."""
    mock_session.execute.return_value.fetchone.return_value = None

    result = find_nearest_template("some clause", contract_type="nda")

    assert result is None


def test_exception_during_search_returns_none_gracefully(mock_session):
    """Any DB exception should be swallowed and return None."""
    mock_session.execute.side_effect = RuntimeError("pgvector blew up")

    result = find_nearest_template("some clause")

    assert result is None


def test_embedding_failure_returns_none_gracefully():
    """If embedding generation fails, we should degrade gracefully."""
    session = MagicMock()
    with (
        patch.object(matcher_module, "_get_sync_session", return_value=session),
        patch.object(
            matcher_module, "generate_embedding", side_effect=RuntimeError("openai down")
        ),
    ):
        result = find_nearest_template("some clause")

    assert result is None


def test_session_always_closed_on_success(mock_session):
    """Session should be closed on the happy path."""
    row = _make_template_row()
    mock_session.execute.return_value.fetchone.return_value = row

    find_nearest_template("some clause")

    mock_session.close.assert_called_once()


def test_session_always_closed_on_exception(mock_session):
    """Session should be closed when an exception is raised."""
    mock_session.execute.side_effect = RuntimeError("boom")

    find_nearest_template("some clause")

    mock_session.close.assert_called_once()


def test_similarity_is_returned_as_float(mock_session):
    """Similarity should always be a plain float, even if DB returns Decimal."""
    from decimal import Decimal

    row = _make_template_row(similarity=Decimal("0.8765"))  # type: ignore
    mock_session.execute.return_value.fetchone.return_value = row

    result = find_nearest_template("some clause")

    assert result is not None
    assert isinstance(result["similarity"], float)
    assert result["similarity"] == pytest.approx(0.8765)


def test_embedding_generated_from_input_text(mock_session, mock_embedding):
    """The embedding function should be called with the exact input text."""
    row = _make_template_row()
    mock_session.execute.return_value.fetchone.return_value = row

    find_nearest_template("very specific clause text", contract_type="nda")

    mock_embedding.assert_called_once_with("very specific clause text")
