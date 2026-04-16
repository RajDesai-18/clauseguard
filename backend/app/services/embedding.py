"""Embedding generation via OpenAI text-embedding-3-small."""

from __future__ import annotations

import logging

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized client
_client: OpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


def _get_client() -> OpenAI:
    """Get or create the OpenAI client singleton."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding vector (1536 dimensions).

    Raises:
        Exception: If the OpenAI API call fails.
    """
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call.

    OpenAI supports batching up to ~8000 tokens per request.
    For longer lists, this function chunks into batches of 50.

    Args:
        texts: List of texts to embed.

    Returns:
        List of embedding vectors in the same order as input texts.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    if not texts:
        return []

    client = _get_client()
    all_embeddings: list[list[float]] = []
    batch_size = 50

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        # Sort by index to preserve order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([item.embedding for item in sorted_data])

    return all_embeddings
