"""Cross-contract semantic clause search via pgvector similarity.

Powers the user-facing search feature: given free-text, embed it and find the
nearest clauses across *only the requesting user's* analysed contracts, ranked
by cosine similarity.

Runs synchronously through psycopg2 (mirroring semantic_cache and
template_matcher) because pgvector's text->vector cast is reliable on psycopg2
but not on asyncpg, where a text-typed bind parameter has no implicit cast to
``vector``. The endpoint calls this from a worker thread so neither the
embedding call nor the DB round-trip blocks the event loop.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def _get_engine() -> Engine:
    """Get or create the cached synchronous engine.

    Unlike semantic_cache/template_matcher (which build an engine per call),
    this caches one engine at module scope so the user-facing search endpoint
    doesn't churn connection pools on every request.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        _engine = create_engine(sync_url, pool_pre_ping=True)
    return _engine


_SEARCH_SQL = text("""
    SELECT
        cl.id            AS clause_id,
        cl.clause_type   AS clause_type,
        cl.risk_level    AS risk_level,
        cl.original_text AS original_text,
        cl.explanation   AS explanation,
        cl.position      AS position,
        ct.id            AS contract_id,
        ct.file_name     AS file_name,
        ct.contract_type AS contract_type,
        ct.overall_risk  AS overall_risk,
        1 - (cl.embedding <=> CAST(:embedding AS vector)) AS similarity
    FROM clauses cl
    JOIN contracts ct ON ct.id = cl.contract_id
    WHERE ct.user_id = :user_id
        AND cl.embedding IS NOT NULL
    ORDER BY cl.embedding <=> CAST(:embedding AS vector)
    LIMIT :limit
""")


def search_clauses(query: str, user_id: str, limit: int = 30) -> list[dict]:
    """Find clauses across the user's contracts most similar to a query.

    Embeds the query text and runs a pgvector cosine-similarity search, scoped
    to the requesting user's clauses only. Results are returned as flat dicts
    ordered by descending similarity; grouping by contract is the caller's job.

    Args:
        query: The free-text search query.
        user_id: The owning user's id; results never cross this boundary.
        limit: Maximum number of clause hits to return.

    Returns:
        A list of hit dicts (clause + parent contract fields + similarity),
        ordered most-similar first, with the sub-threshold tail trimmed.

    Raises:
        Exception: If embedding generation or the DB query fails. The caller
            translates this into an API error.
    """
    embedding = generate_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    with Session(_get_engine()) as session:
        rows = (
            session.execute(
                _SEARCH_SQL,
                {"embedding": embedding_str, "user_id": user_id, "limit": limit},
            )
            .mappings()
            .all()
        )

    raw_hits: list[dict] = [
        {
            "clause_id": str(row["clause_id"]),
            "clause_type": row["clause_type"],
            "risk_level": row["risk_level"],
            "original_text": row["original_text"],
            "explanation": row["explanation"],
            "position": row["position"],
            "contract_id": str(row["contract_id"]),
            "file_name": row["file_name"],
            "contract_type": row["contract_type"],
            "overall_risk": row["overall_risk"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]

    if not raw_hits:
        return []

    # Rows arrive most-similar first, so the first is the global best match.
    # Floor is the stricter of the absolute backstop and a fraction of the top
    # score, so the cutoff adapts to how well the query matched at all.
    top = raw_hits[0]["similarity"]
    floor = max(settings.search_min_similarity, settings.search_relative_floor * top)
    hits = [h for h in raw_hits if h["similarity"] >= floor]

    logger.info(
        "Clause search: user=%s query_len=%d candidates=%d hits=%d top=%.4f",
        user_id,
        len(query),
        len(raw_hits),
        len(hits),
        top,
    )
    return hits
