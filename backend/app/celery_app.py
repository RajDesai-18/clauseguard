"""Celery application configuration."""

import logging

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings
from app.core.tracing import install_log_trace_filter, setup_tracing

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
        "app.tasks.finalize.*": {"queue": "analyze"},
        "app.tasks.dispatchers.*": {"queue": "default"},
    },
    task_default_retry_delay=2,
    task_max_retries=3,
    worker_log_format=(
        "%(asctime)s | %(levelname)s | %(processName)s | trace_id=%(otelTraceID)s | %(message)s"
    ),
    worker_task_log_format=(
        "%(asctime)s | %(levelname)s | %(processName)s | %(task_name)s "
        "| trace_id=%(otelTraceID)s | %(message)s"
    ),
)


@worker_process_init.connect
def init_worker_tracing(**_kwargs: object) -> None:
    """Install the tracer provider in each worker process after fork.

    Celery uses a prefork pool, so the tracer provider and its exporter's
    background thread must be created inside each child process, not at module
    import in the parent. The `worker_process_init` signal fires once per
    forked worker process, which is the correct place to do this: a provider
    (and its BatchSpanProcessor export thread) set up before the fork would not
    survive into the children, and spans would silently never export.
    """
    setup_tracing("worker")
    install_log_trace_filter()


# Tasks are imported explicitly in app/tasks/__init__.py.
# Autodiscovery is intentionally not used because it can silently
# skip modules with import errors, masking real problems.
import app.tasks  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]


@celery_app.task(name="app.tasks.ping")
def ping() -> str:
    """Health check task to verify Celery is working."""
    logger.info("Celery ping task executed")
    return "pong"
