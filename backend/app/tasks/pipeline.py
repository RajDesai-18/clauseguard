from __future__ import annotations

import logging

from celery import chain
from celery.result import AsyncResult

from app.tasks.classify import classify_clauses_task
from app.tasks.dispatchers import dispatch_analysis_task
from app.tasks.parse import parse_document_task

logger = logging.getLogger(__name__)


def run_pipeline(contract_id: str) -> AsyncResult:
    """Build and dispatch the contract analysis saga.

    Note: this is a regular Python function, not a Celery task.
    It constructs the chain and applies it asynchronously, returning
    the AsyncResult of the chain head. The remaining saga stages
    are dispatched dynamically by the dispatcher tasks as earlier
    stages complete.

    Args:
        contract_id: UUID of the contract to process.

    Returns:
        AsyncResult for the chain head (parse task), useful for
        testing and observability.
    """
    logger.info("Dispatching pipeline for contract %s", contract_id)

    pipeline = chain(
        parse_document_task.s(contract_id),  # type: ignore
        classify_clauses_task.s(),  # type: ignore
        dispatch_analysis_task.s(),  # type: ignore
    )
    return pipeline.apply_async()  # type: ignore
