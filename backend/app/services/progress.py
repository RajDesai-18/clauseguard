"""Redis Pub/Sub progress publisher for contract processing pipeline."""

from __future__ import annotations

import json
import logging
import uuid

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "contract:progress:"


async def publish_progress(
    contract_id: uuid.UUID | str,
    status: str,
    detail: str = "",
    current_step: int = 0,
    total_steps: int = 5,
) -> None:
    """Publish a processing progress event to Redis Pub/Sub.

    Args:
        contract_id: The contract being processed.
        status: Current pipeline status (e.g. "parsing", "analyzing").
        detail: Human-readable detail message.
        current_step: Current step number (1-5).
        total_steps: Total pipeline steps.
    """
    redis = await get_redis()
    channel = f"{CHANNEL_PREFIX}{contract_id}"
    payload = json.dumps(
        {
            "contract_id": str(contract_id),
            "status": status,
            "detail": detail,
            "current_step": current_step,
            "total_steps": total_steps,
        }
    )
    try:
        await redis.publish(channel, payload)
        logger.info("Published progress: contract=%s status=%s", contract_id, status)
    except Exception:
        logger.exception("Failed to publish progress for contract %s", contract_id)


def publish_progress_sync(
    contract_id: uuid.UUID,
    status: str,
    detail: str = "",
    current_step: int = 0,
    total_steps: int = 5,
) -> None:
    """Synchronous version for use inside Celery tasks.

    Uses a standalone Redis connection (not async).
    """
    import redis as sync_redis

    from app.core.config import settings

    channel = f"{CHANNEL_PREFIX}{contract_id}"
    payload = json.dumps(
        {
            "contract_id": str(contract_id),
            "status": status,
            "detail": detail,
            "current_step": current_step,
            "total_steps": total_steps,
        }
    )
    try:
        r = sync_redis.from_url(settings.redis_url)
        r.publish(channel, payload)
        r.close()
        logger.info("Published progress (sync): contract=%s status=%s", contract_id, status)
    except Exception:
        logger.exception("Failed to publish progress (sync) for contract %s", contract_id)
