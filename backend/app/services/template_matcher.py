"""Match clauses against market-standard templates via pgvector similarity."""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous DB session."""
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return Session(engine)


def find_nearest_template(
    clause_text: str,
    contract_type: str | None = None,
) -> dict | None:
    """Find the nearest market-standard template for a clause.

    Searches the clause_templates table using pgvector cosine similarity.
    Optionally filters by contract type for more relevant matches.

    Args:
        clause_text: The clause text to match against templates.
        contract_type: Optional contract type to filter templates (nda, msa, etc.).

    Returns:
        A dict with clause_type, standard_text, similarity, and source
        if a match is found, or None.
    """
    session = _get_sync_session()
    try:
        embedding = generate_embedding(clause_text)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        if contract_type:
            result = session.execute(
                text("""
                    SELECT
                        clause_type,
                        standard_text,
                        source,
                        1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                    FROM clause_templates
                    WHERE contract_type = :contract_type
                        AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT 1
                """),
                {"embedding": embedding_str, "contract_type": contract_type},
            ).fetchone()
        else:
            result = session.execute(
                text("""
                    SELECT
                        clause_type,
                        standard_text,
                        source,
                        1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                    FROM clause_templates
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT 1
                """),
                {"embedding": embedding_str},
            ).fetchone()

        if result is None:
            logger.debug("No templates found for matching")
            return None

        logger.info(
            "Template match: clause_type=%s, similarity=%.4f",
            result.clause_type,
            result.similarity,
        )

        return {
            "clause_type": result.clause_type,
            "standard_text": result.standard_text,
            "similarity": float(result.similarity),
            "source": result.source,
        }

    except Exception:
        logger.exception("Template matching failed")
        return None
    finally:
        session.close()
