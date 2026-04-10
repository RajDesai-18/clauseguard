"""Celery task definitions."""

from app.tasks.parse import parse_document_task  # noqa: F401
from app.tasks.pipeline import run_pipeline  # noqa: F401
