"""Step 5: Generate embeddings, persist, and mark contract complete."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.embedding import generate_embeddings_batch
from app.services.progress import publish_progress_sync
from app.tasks._session import get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.finalize.finalize_contract_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=180,
)
def finalize_contract_task(self, redline_result: dict) -> dict:
    """Generate clause embeddings, persist, and mark the contract complete.

    Embeddings are generated in a single batched call to OpenAI for cost
    efficiency. Done last so that the semantic cache (populated from the
    `clauses` table) only contains clauses with full analysis attached.

    Args:
        redline_result: Dict from redlines_complete_task containing contract_id.

    Returns:
        Dict summarizing the completed pipeline.
    """
    contract_id = redline_result["contract_id"]
    logger.info("Finalizing contract %s", contract_id)

    publish_progress_sync(
        contract_id,
        status="scoring",
        detail="Generating embeddings and saving results",
        current_step=5,
    )

    session = get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")

        clauses = (
            session.query(Clause)
            .filter(Clause.contract_id == contract.id)
            .order_by(Clause.position)
            .all()
        )
        if not clauses:
            raise ValueError(f"No clauses found for contract {contract_id}")

        # Generate embeddings only for clauses that don't already have one.
        # On retry after a partial failure, this avoids redundant API calls.
        clauses_needing_embedding = [c for c in clauses if c.embedding is None]

        if clauses_needing_embedding:
            texts = [c.original_text for c in clauses_needing_embedding]
            try:
                embeddings = generate_embeddings_batch(texts)
            except Exception:
                logger.exception(
                    "Failed to generate embeddings for contract %s; "
                    "completing without semantic cache contribution",
                    contract_id,
                )
                # Don't fail the whole pipeline if embeddings fail.
                # The contract is still usable; it just won't contribute
                # to the semantic cache.
                embeddings = [None] * len(clauses_needing_embedding)

            for clause, embedding in zip(clauses_needing_embedding, embeddings, strict=True):
                clause.embedding = embedding

            logger.info(
                "Generated %d embeddings for contract %s",
                sum(1 for e in embeddings if e is not None),
                contract_id,
            )
        else:
            logger.info(
                "All clauses for contract %s already have embeddings",
                contract_id,
            )

        # Mark complete
        contract.status = "complete"
        session.commit()

        publish_progress_sync(
            contract_id,
            status="complete",
            detail=(
                f"Analysis complete: {contract.clause_count} clauses, "
                f"overall risk: {contract.overall_risk}"
            ),
            current_step=5,
        )

        logger.info(
            "Pipeline complete for contract %s: %d clauses, risk=%s",
            contract_id,
            contract.clause_count,
            contract.overall_risk,
        )

        return {
            "contract_id": contract_id,
            "status": "complete",
            "contract_type": contract.contract_type,
            "clause_count": contract.clause_count,
            "overall_risk": contract.overall_risk,
        }

    except Exception as exc:
        logger.exception("Finalize failed for contract %s", contract_id)
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
            detail=f"Finalize failed: {exc}",
            current_step=5,
        )
        raise
    finally:
        session.close()
