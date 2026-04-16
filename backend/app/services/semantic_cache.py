"""Semantic clause caching via pgvector similarity search."""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


def _get_sync_session() -> Session:
    """Create a synchronous DB session."""
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return Session(engine)


def find_similar_clause(clause_text: str) -> dict | None:
    """Search for a semantically similar previously-analyzed clause.

    Uses pgvector cosine similarity to find the nearest match
    in the clauses table. If similarity exceeds the threshold,
    returns the cached analysis to skip the LLM call.

    Args:
        clause_text: The clause text to search for.

    Returns:
        A dict with risk_level, confidence, explanation, and
        market_comparison if a match is found, or None.
    """
    session = _get_sync_session()
    try:
        embedding = generate_embedding(clause_text)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        result = session.execute(
            text("""
                SELECT
                    clause_type,
                    risk_level,
                    confidence,
                    explanation,
                    market_comparison,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM clauses
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT 1
            """),
            {"embedding": embedding_str},
        ).fetchone()

        if result is None:
            logger.debug("No existing clauses with embeddings found")
            return None

        similarity = result.similarity

        if similarity >= SIMILARITY_THRESHOLD:
            logger.info(
                "Semantic cache hit: clause_type=%s, similarity=%.4f",
                result.clause_type,
                similarity,
            )
            return {
                "risk_level": result.risk_level,
                "confidence": float(result.confidence) if result.confidence else 0.0,
                "explanation": result.explanation,
                "market_comparison": result.market_comparison,
            }

        logger.debug(
            "Nearest clause similarity %.4f below threshold %.2f",
            similarity,
            SIMILARITY_THRESHOLD,
        )
        return None

    except Exception:
        logger.exception("Semantic cache search failed, falling back to LLM")
        return None
    finally:
        session.close()
