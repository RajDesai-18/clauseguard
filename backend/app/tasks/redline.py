"""Step 4: Generate redlines for risky clauses (fan-out)."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.progress import publish_progress_sync
from app.services.redline_generator import generate_redline
from app.tasks._session import get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.redline.generate_one_redline_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    soft_time_limit=60,
    time_limit=90,
)
def generate_one_redline_task(self, clause_id: str) -> dict:
    """Generate a suggested redline for a single risky clause.

    Reads the clause from the DB, calls the redline generator, and
    persists the result. Skips green clauses defensively even though
    the orchestrator should not send those here.

    Args:
        clause_id: UUID of the clause to redline.

    Returns:
        Dict with clause_id and whether a redline was generated.
    """
    logger.info("Generating redline for clause %s", clause_id)

    session = get_sync_session()
    try:
        clause = session.get(Clause, uuid.UUID(clause_id))
        if clause is None:
            raise ValueError(f"Clause {clause_id} not found")

        # Defensive guard: redline generator already returns None for green,
        # but skip the LLM call entirely when we know we don't need it.
        if clause.risk_level not in ("yellow", "red"):
            logger.info(
                "Skipping redline for green clause %s (%s)",
                clause_id,
                clause.clause_type,
            )
            return {"clause_id": clause_id, "redlined": False}

        if not clause.explanation:
            logger.warning(
                "Clause %s has no explanation; redline quality may suffer",
                clause_id,
            )

        contract = session.get(Contract, clause.contract_id)
        contract_type = (contract.contract_type if contract else None) or "other"

        redline = generate_redline(
            clause_text=clause.original_text,
            clause_type=clause.clause_type,
            contract_type=contract_type,
            risk_level=clause.risk_level,
            explanation=clause.explanation or "",
        )

        clause.suggested_redline = redline
        session.commit()

        logger.info(
            "Generated redline for clause %s (%s, %s)",
            clause_id,
            clause.clause_type,
            clause.risk_level,
        )

        return {"clause_id": clause_id, "redlined": redline is not None}

    except Exception:
        logger.exception("Failed to generate redline for clause %s", clause_id)
        # Re-raise to trigger retry. If retries exhaust, we leave
        # suggested_redline=None and the chord callback proceeds.
        raise
    finally:
        session.close()


@celery_app.task(
    name="app.tasks.redline.redlines_complete_task",
    bind=True,
    max_retries=1,
    soft_time_limit=20,
    time_limit=30,
)
def redlines_complete_task(self, _redline_results: list, contract_id: str) -> dict:
    """Chord callback after all redline generations finish.

    Logs a summary and emits a progress event. The actual redline
    text is already persisted by the per-clause tasks.

    Args:
        _redline_results: List of dicts from generate_one_redline_task.
        contract_id: UUID of the contract.

    Returns:
        Dict with contract_id for the next chain step.
    """
    redlined_count = sum(1 for r in _redline_results if isinstance(r, dict) and r.get("redlined"))
    failed_count = sum(1 for r in _redline_results if not isinstance(r, dict))

    logger.info(
        "Redlines complete for contract %s: %d generated, %d failed",
        contract_id,
        redlined_count,
        failed_count,
    )

    publish_progress_sync(
        contract_id,  # type: ignore
        status="scoring",
        detail=f"Generated {redlined_count} suggested revisions",
        current_step=4,
    )

    return {
        "contract_id": contract_id,
        "redlined_count": redlined_count,
        "failed_count": failed_count,
    }
