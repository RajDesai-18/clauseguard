"""Saga orchestrator: contract processing pipeline."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings
from app.core.storage import download_file
from app.models.contract import Contract
from app.services.document_parser import parse_document
from app.services.progress import publish_progress_sync

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous DB session for Celery tasks."""
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return Session(engine)


@celery_app.task(name="app.tasks.pipeline.run_pipeline", bind=True, max_retries=0)
def run_pipeline(self, contract_id: str) -> dict:
    """Orchestrate the full contract analysis pipeline.

    Steps: parse -> classify -> score -> redline -> finalize.
    """
    logger.info("Pipeline started for contract %s", contract_id)
    publish_progress_sync(
        contract_id,  # type: ignore
        status="parsing",
        detail="Pipeline started",
        current_step=1,
    )

    session = _get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")

        # Step 1: Parse document
        contract.status = "parsing"
        session.commit()

        file_bytes = download_file(contract.file_url)
        raw_text = parse_document(file_bytes, contract.file_name)

        contract.raw_text = raw_text
        contract.status = "parsed"
        session.commit()

        publish_progress_sync(
            contract_id,  # type: ignore
            status="parsed",
            detail=f"Extracted {len(raw_text)} characters",
            current_step=1,
        )
        logger.info("Parsed contract %s: %d chars", contract_id, len(raw_text))

        # Steps 2-4 are placeholders for Phase 3
        publish_progress_sync(
            contract_id,  # type: ignore
            status="complete",
            detail="Parsing complete. AI analysis coming in Phase 3.",
            current_step=5,
        )

        # Finalize
        contract.status = "complete"
        session.commit()

        logger.info("Pipeline finished for contract %s", contract_id)
        return {"contract_id": contract_id, "status": "complete"}

    except Exception:
        logger.exception("Pipeline failed for contract %s", contract_id)
        try:
            contract = session.get(Contract, uuid.UUID(contract_id))
            if contract is not None:
                contract.status = "failed"
                session.commit()
        except Exception:
            logger.exception("Failed to update status to failed")
        publish_progress_sync(
            contract_id,  # type: ignore
            status="failed",
            detail="Pipeline failed",
            current_step=0,
        )
        raise
    finally:
        session.close()
