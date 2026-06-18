"""Dispatcher tasks that build chord groups dynamically.

Chord groups need clause IDs that don't exist until earlier saga
steps have run. These small tasks read the IDs from the DB and
construct the next chord at runtime, then return their input
unchanged so the surrounding chain continues normally.
"""

from __future__ import annotations

import logging
import uuid

from celery import chain, chord, group

from app.celery_app import celery_app
from app.models.clause import Clause
from app.tasks._session import get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.dispatchers.dispatch_analysis_task",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=2,
    soft_time_limit=30,
    time_limit=60,
)
def dispatch_analysis_task(self, classify_result: dict) -> dict:
    """Read clause IDs from the DB and dispatch the analysis chord.

    Receives the classify task's return value. Builds:
        chord(
            group(analyze_one_clause_task.s(id) for each clause),
            chain(
                score_contract_task,
                dispatch_redlines_task,
                redlines_complete_task,
                finalize_contract_task,
            ),
        )

    Returns the classify_result unchanged so callers (e.g., tests)
    can still inspect what was dispatched.
    """
    # Local imports avoid circular dependency at module load time.
    from app.tasks.score import analyze_one_clause_task, score_contract_task

    contract_id = classify_result["contract_id"]
    logger.info("Dispatching analysis chord for contract %s", contract_id)

    session = get_sync_session()
    try:
        clauses = (
            session.query(Clause.id)
            .filter(Clause.contract_id == uuid.UUID(contract_id))
            .order_by(Clause.position)
            .all()
        )
        clause_ids = [str(row[0]) for row in clauses]
    finally:
        session.close()

    if not clause_ids:
        raise ValueError(f"Contract {contract_id} has no clauses to analyze")

    logger.info(
        "Dispatching %d parallel analysis tasks for contract %s",
        len(clause_ids),
        contract_id,
    )

    # Build the chord. The callback is itself a chain that runs
    # score -> dispatch_redlines -> redlines_complete -> finalize.
    analysis_chord = chord(
        group(analyze_one_clause_task.s(cid) for cid in clause_ids),  # type: ignore
        chain(
            score_contract_task.s(contract_id),  # type: ignore
            dispatch_redlines_task.s(),  # type: ignore
            # redlines_complete_task and finalize_contract_task are
            # appended inside dispatch_redlines_task as part of its
            # nested chord callback chain.
        ),
    )
    analysis_chord.apply_async()

    return {**classify_result, "dispatched_clause_count": len(clause_ids)}


@celery_app.task(
    name="app.tasks.dispatchers.dispatch_redlines_task",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=2,
    soft_time_limit=30,
    time_limit=60,
)
def dispatch_redlines_task(self, score_result: dict) -> dict:
    """Read risky clause IDs and dispatch the redline chord.

    If there are no risky clauses, skips the chord and dispatches
    finalize directly so the contract still gets marked complete.
    """
    from app.tasks.finalize import finalize_contract_task
    from app.tasks.redline import generate_one_redline_task, redlines_complete_task

    contract_id = score_result["contract_id"]
    logger.info("Dispatching redline chord for contract %s", contract_id)

    session = get_sync_session()
    try:
        risky_clauses = (
            session.query(Clause.id)
            .filter(Clause.contract_id == uuid.UUID(contract_id))
            .filter(Clause.risk_level.in_(["yellow", "red"]))
            .order_by(Clause.position)
            .all()
        )
        risky_clause_ids = [str(row[0]) for row in risky_clauses]
    finally:
        session.close()

    if not risky_clause_ids:
        # No redlines needed. Skip the chord and go straight to finalize.
        logger.info(
            "Contract %s has no risky clauses; skipping redline chord",
            contract_id,
        )
        # Hand finalize a payload shaped like redlines_complete_task's return
        finalize_contract_task.apply_async(  # type: ignore
            args=[{"contract_id": contract_id, "redlined_count": 0, "failed_count": 0}],
        )
        return {**score_result, "dispatched_redline_count": 0}

    logger.info(
        "Dispatching %d parallel redline tasks for contract %s",
        len(risky_clause_ids),
        contract_id,
    )

    redline_chord = chord(
        group(generate_one_redline_task.s(cid) for cid in risky_clause_ids),  # type: ignore
        chain(
            redlines_complete_task.s(contract_id),  # type: ignore
            finalize_contract_task.s(),  # type: ignore
        ),
    )
    redline_chord.apply_async()

    return {**score_result, "dispatched_redline_count": len(risky_clause_ids)}
