"""Health check endpoint."""

import asyncio
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

HEALTH_CHECK_TIMEOUT = 3  # seconds per service check


@router.get("/health")
async def health_check() -> dict:
    """Aggregated health check for all services."""
    results: dict = {
        "status": "healthy",
        "services": {},
    }

    # Check PostgreSQL
    try:
        from sqlalchemy import text

        from app.core.database import get_session_factory

        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            async with get_session_factory()() as session:
                await session.execute(text("SELECT 1"))
        results["services"]["postgres"] = "healthy"
    except Exception as e:
        logger.error("PostgreSQL health check failed: %s", e)
        results["services"]["postgres"] = "unhealthy"
        results["status"] = "degraded"

    # Check Redis
    try:
        from app.core.redis import get_redis

        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            redis = await get_redis()
            await redis.ping()
        results["services"]["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        results["services"]["redis"] = "unhealthy"
        results["status"] = "degraded"

    # Check RabbitMQ (via Celery)
    try:
        from app.celery_app import celery_app

        conn = celery_app.connection()
        conn.ensure_connection(max_retries=1, timeout=HEALTH_CHECK_TIMEOUT)
        conn.close()
        results["services"]["rabbitmq"] = "healthy"
    except Exception as e:
        logger.error("RabbitMQ health check failed: %s", e)
        results["services"]["rabbitmq"] = "unhealthy"
        results["status"] = "degraded"

    # Check MinIO
    try:
        from app.core.storage import get_s3_client

        client = get_s3_client()
        client.list_buckets()
        results["services"]["minio"] = "healthy"
    except Exception as e:
        logger.error("MinIO health check failed: %s", e)
        results["services"]["minio"] = "unhealthy"
        results["status"] = "degraded"

    return results
