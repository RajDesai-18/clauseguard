"""Step 2: Split parsed text into classified clauses."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.clause_splitter import split_clauses
from app.services.llm_client import LLMUnavailableError
from app.services.progress import publish_progress_sync
from app.tasks._session import get_sync_session

logger = logging.getLogger(__name__)

# Shown to the user when the document was parsed but the LLM was
# unreachable, so no clauses could be segmented or analysed.
SPLIT_DEGRADED_REASON = (
    "AI analysis is temporarily unavailable, so this contract was saved "
    "without clause-by-clause review. The original document is intact; "
    "re-upload it later to run a full analysis."
)


@celery_app.task(
    name="app.tasks.classify.classify_clauses_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=180,
)
def classify_clauses_task(self, parse_result: dict) -> dict:
    """Split parsed contract text into individual clauses.

    Reads contract.raw_text (set by parse_document_task), calls the
    LLM splitter, and persists one Clause row per detected clause
    with risk fields left null for the analyze step to fill in.

    Graceful degradation: if the LLM is unreachable (both primary and
    fallback down), the document cannot be segmented. Rather than fail,
    the contract is marked ``complete`` with a ``degraded_reason`` and
    the remaining saga chain is cleared so no analysis is attempted.
    The parsed ``raw_text`` is preserved and the contract stays viewable.

    Args:
        parse_result: Dict from the previous task containing contract_id.

    Returns:
        Dict with contract_id and clause_count for the next task.
    """
    contract_id = parse_result["contract_id"]
    logger.info("Classifying clauses for contract %s", contract_id)

    publish_progress_sync(
        contract_id,
        status="analyzing",
        detail="Splitting contract into clauses",
        current_step=2,
    )

    session = get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")
        if not contract.raw_text:
            raise ValueError(f"Contract {contract_id} has no raw_text; parse step did not run")

        contract.status = "analyzing"
        session.commit()

        # Call LLM to split + classify. This is the first LLM dependency
        # in the pipeline; if it's down, we degrade rather than fail.
        try:
            split_result = split_clauses(contract.raw_text)
        except LLMUnavailableError:
            return _degrade_at_split(self, session, contract, contract_id)

        contract_type = split_result.get("contract_type", "other")
        summary = split_result.get("summary", "")
        raw_clauses = split_result.get("clauses", [])

        if not raw_clauses:
            raise ValueError(f"Splitter returned zero clauses for contract {contract_id}")

        # Persist contract-level metadata
        contract.contract_type = contract_type
        contract.summary = summary
        contract.clause_count = len(raw_clauses)

        # Persist one Clause row per detected clause.
        # Risk fields are left null; analyze_clause_task will fill them in.
        for i, raw_clause in enumerate(raw_clauses, 1):
            clause = Clause(
                contract_id=contract.id,
                clause_type=raw_clause.get("clause_type", "unknown"),
                original_text=raw_clause.get("original_text", ""),
                position=raw_clause.get("position", i),
                risk_level=None,
                explanation=None,
                market_comparison=None,
                suggested_redline=None,
                confidence=None,
                embedding=None,
            )
            session.add(clause)

        session.commit()

        publish_progress_sync(
            contract_id,
            status="analyzing",
            detail=(f"Detected {len(raw_clauses)} clauses in {contract_type} contract"),
            current_step=2,
        )

        logger.info(
            "Classified contract %s: type=%s, %d clauses",
            contract_id,
            contract_type,
            len(raw_clauses),
        )

        return {
            "contract_id": contract_id,
            "contract_type": contract_type,
            "clause_count": len(raw_clauses),
        }

    except Exception as exc:
        logger.exception("Classification failed for contract %s", contract_id)
        try:
            contract = session.get(Contract, uuid.UUID(contract_id))
            if contract is not None:
                contract.status = "failed"
                session.commit()
        except Exception:
            logger.exception("Failed to mark contract as failed")
        publish_progress_sync(
            contract_id,
            status="failed",
            detail=f"Classification failed: {exc}",
            current_step=2,
        )
        raise
    finally:
        session.close()


def _degrade_at_split(task, session, contract: Contract, contract_id: str) -> dict:
    """Mark a contract complete-but-degraded when the LLM is unavailable.

    Clears the remaining saga chain so dispatch_analysis_task does not
    run (there are no clauses to analyse), preserves the parsed text,
    and records a user-facing reason. Emits a terminal ``complete``
    progress event so the frontend stops the live tracker and renders
    the degraded state.
    """
    logger.warning(
        "LLM unavailable while splitting contract %s; completing in degraded mode",
        contract_id,
    )

    # Clear the rest of the chain (dispatch_analysis_task) so nothing
    # downstream runs. Without this, the chain would proceed and fail on
    # the zero-clause guard.
    task.request.chain = None

    contract.status = "complete"
    contract.degraded_reason = SPLIT_DEGRADED_REASON
    contract.clause_count = 0
    session.commit()

    publish_progress_sync(
        contract_id,  # type: ignore
        status="complete",
        detail="Saved without AI analysis (analysis service unavailable)",
        current_step=5,
    )

    return {
        "contract_id": contract_id,
        "contract_type": None,
        "clause_count": 0,
        "degraded": True,
    }
