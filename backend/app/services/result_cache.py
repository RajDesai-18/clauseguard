"""Async read-through cache for completed contract analysis results.

Distinct from ``services/cache.py``, which is the synchronous, per-clause
LLM cache used inside Celery tasks. This module caches the *assembled*
clause-list response for a completed contract on the async API read path.

Only ``complete`` contracts are cached: their analysis is immutable
(re-uploading a file creates a new contract rather than re-analysing an
existing one), so a cached payload cannot go stale within its TTL. The
cache is invalidated explicitly on delete.

This module manages its own ``redis.asyncio`` client rather than sharing
the pub/sub singleton in ``core/redis.py``. A single shared async client
binds its connection pool to the first event loop that touches it, which
breaks when reused across loops; constructing the client lazily and
letting redis-py manage the pool per running loop avoids that class of
bug. Every operation fails open: a Redis problem must never break a read,
it just falls through to PostgreSQL.
"""

from __future__ import annotations

import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def _client() -> redis.Redis:
    """Construct a Redis client bound to the current running loop.

    redis-py reuses an internal connection pool keyed appropriately, so
    constructing per call is cheap and avoids the cross-loop binding that
    a module-level singleton suffers under ASGI.
    """
    return redis.from_url(settings.redis_url, decode_responses=True)


def _clauses_key(contract_id: str) -> str:
    """Cache key for a contract's assembled clause-list response."""
    return f"contract:clauses:{contract_id}"


async def get_cached_clauses(contract_id: str) -> str | None:
    """Return the cached clause-list JSON string, or None on miss/error.

    Returns the raw JSON string (not a parsed object) so the caller can
    serve it directly, skipping a round of Pydantic validation.
    """
    client = _client()
    try:
        cached = await client.get(_clauses_key(contract_id))
        if cached is not None:
            logger.debug("Analysis cache hit for contract %s", contract_id)
        return cached
    except Exception:
        logger.warning(
            "Analysis cache read failed for contract %s, falling through to DB",
            contract_id,
        )
        return None
    finally:
        await client.aclose()


async def set_cached_clauses(contract_id: str, payload: str) -> None:
    """Cache the assembled clause-list JSON for a completed contract."""
    client = _client()
    try:
        await client.setex(
            _clauses_key(contract_id),
            settings.analysis_cache_ttl_seconds,
            payload,
        )
        logger.debug("Cached analysis result for contract %s", contract_id)
    except Exception:
        logger.warning(
            "Analysis cache write failed for contract %s, continuing",
            contract_id,
        )
    finally:
        await client.aclose()


async def invalidate_contract_cache(contract_id: str) -> None:
    """Drop any cached analysis for a contract (called on delete)."""
    client = _client()
    try:
        await client.delete(_clauses_key(contract_id))
        logger.debug("Invalidated analysis cache for contract %s", contract_id)
    except Exception:
        logger.warning(
            "Analysis cache invalidation failed for contract %s",
            contract_id,
        )
    finally:
        await client.aclose()
