"""Celery application configuration."""

import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "clauseguard",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_queues={
        "default": {},
        "parse": {},
        "analyze": {},
        "dlq": {},
    },
    task_routes={
        "app.tasks.parse.*": {"queue": "parse"},
        "app.tasks.classify.*": {"queue": "analyze"},
        "app.tasks.score.*": {"queue": "analyze"},
        "app.tasks.redline.*": {"queue": "analyze"},
    },
    task_default_retry_delay=2,
    task_max_retries=3,
)

celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task(name="app.tasks.ping")
def ping() -> str:
    """Health check task to verify Celery is working."""
    logger.info("Celery ping task executed")
    return "pong"
