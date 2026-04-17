"""Tests for the embedding service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import embedding as embedding_module
from app.services.embedding import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    generate_embedding,
    generate_embeddings_batch,
)


def _make_embedding_response(vectors: list[list[float]]) -> MagicMock:
    """Build a mock OpenAI embeddings response with the given vectors."""
    response = MagicMock()
    response.data = [MagicMock(embedding=vec, index=i) for i, vec in enumerate(vectors)]
    return response


@pytest.fixture(autouse=True)
def reset_client_singleton():
    """Reset the lazy-initialized OpenAI client between tests."""
    embedding_module._client = None
    yield
    embedding_module._client = None


def test_generate_embedding_returns_vector():
    """generate_embedding should return a list of floats from the API response."""
    fake_vector = [0.1] * EMBEDDING_DIMENSION
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _make_embedding_response([fake_vector])

    with patch.object(embedding_module, "_get_client", return_value=mock_client):
        result = generate_embedding("some clause text")

    assert result == fake_vector
    mock_client.embeddings.create.assert_called_once_with(
        model=EMBEDDING_MODEL,
        input="some clause text",
    )


def test_generate_embeddings_batch_empty_returns_empty():
    """Empty input should short-circuit without calling the API."""
    mock_client = MagicMock()

    with patch.object(embedding_module, "_get_client", return_value=mock_client):
        result = generate_embeddings_batch([])

    assert result == []
    mock_client.embeddings.create.assert_not_called()


def test_generate_embeddings_batch_single_batch():
    """A small list should be embedded in a single API call."""
    vectors = [[0.1] * EMBEDDING_DIMENSION, [0.2] * EMBEDDING_DIMENSION]
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _make_embedding_response(vectors)

    with patch.object(embedding_module, "_get_client", return_value=mock_client):
        result = generate_embeddings_batch(["clause one", "clause two"])

    assert result == vectors
    assert mock_client.embeddings.create.call_count == 1


def test_generate_embeddings_batch_chunks_over_50():
    """Lists longer than 50 should be split into multiple API calls."""
    texts = [f"clause {i}" for i in range(120)]
    # Each API call returns vectors matching the batch size it was given
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = [
        _make_embedding_response([[float(i)] * EMBEDDING_DIMENSION for i in range(50)]),
        _make_embedding_response([[float(i)] * EMBEDDING_DIMENSION for i in range(50, 100)]),
        _make_embedding_response([[float(i)] * EMBEDDING_DIMENSION for i in range(100, 120)]),
    ]

    with patch.object(embedding_module, "_get_client", return_value=mock_client):
        result = generate_embeddings_batch(texts)

    assert len(result) == 120
    assert mock_client.embeddings.create.call_count == 3
    # Verify batch sizes passed to the API
    call_sizes = [
        len(call.kwargs["input"]) for call in mock_client.embeddings.create.call_args_list
    ]
    assert call_sizes == [50, 50, 20]


def test_generate_embeddings_batch_preserves_order():
    """Response data out of order (by index) should be sorted correctly."""
    # Simulate OpenAI returning items with shuffled indices
    response = MagicMock()
    response.data = [
        MagicMock(embedding=[3.0], index=2),
        MagicMock(embedding=[1.0], index=0),
        MagicMock(embedding=[2.0], index=1),
    ]
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = response

    with patch.object(embedding_module, "_get_client", return_value=mock_client):
        result = generate_embeddings_batch(["a", "b", "c"])

    assert result == [[1.0], [2.0], [3.0]]


def test_client_singleton_is_reused():
    """_get_client should return the same instance across calls."""
    with patch.object(embedding_module, "OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value = MagicMock()

        first = embedding_module._get_client()
        second = embedding_module._get_client()

    assert first is second
    mock_openai_cls.assert_called_once()
