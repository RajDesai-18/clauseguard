"""Redis caching helpers for LLM responses and analysis results."""

from __future__ import annotations

import hashlib
import json
import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default TTL: 24 hours
DEFAULT_TTL = 86400


def _get_sync_redis() -> redis.Redis:
    """Create a synchronous Redis client for use in Celery tasks."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def _clause_cache_key(clause_text: str, contract_type: str) -> str:
    """Generate a cache key from clause text and contract type."""
    content = f"{contract_type}:{clause_text}"
    return f"clause:analysis:{hashlib.sha256(content.encode()).hexdigest()}"


def get_cached_analysis(clause_text: str, contract_type: str) -> dict | None:
    """Check Redis for a cached clause analysis.

    Args:
        clause_text: The exact text of the clause.
        contract_type: Type of contract (e.g. nda, msa, lease).

    Returns:
        Cached analysis dict if found, None otherwise.
    """
    try:
        client = _get_sync_redis()
        key = _clause_cache_key(clause_text, contract_type)
        cached = client.get(key)
        if cached is not None:
            logger.debug("Cache hit for clause: %s", key[:40])
            return json.loads(cached)  # type: ignore
        return None
    except Exception:
        logger.warning("Redis cache read failed, proceeding without cache")
        return None


def set_cached_analysis(
    clause_text: str,
    contract_type: str,
    analysis: dict,
    ttl: int = DEFAULT_TTL,
) -> None:
    """Cache a clause analysis result in Redis.

    Args:
        clause_text: The exact text of the clause.
        contract_type: Type of contract (e.g. nda, msa, lease).
        analysis: The analysis dict (risk_level, explanation, etc.).
        ttl: Time-to-live in seconds (default 24 hours).
    """
    try:
        client = _get_sync_redis()
        key = _clause_cache_key(clause_text, contract_type)
        client.setex(key, ttl, json.dumps(analysis))
        logger.debug("Cached analysis for clause: %s", key[:40])
    except Exception:
        logger.warning("Redis cache write failed, continuing without cache")
