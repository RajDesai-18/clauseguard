"""Step 1: Parse uploaded document and extract text."""

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


@celery_app.task(
    name="app.tasks.parse.parse_document_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def parse_document_task(self, contract_id: str) -> dict:
    """Download file from MinIO, extract text, save to DB.

    Args:
        contract_id: UUID of the contract to parse.

    Returns:
        Dict with contract_id and extracted char count.
    """
    logger.info("Parsing document for contract %s", contract_id)
    publish_progress_sync(
        contract_id,  # type: ignore
        status="parsing",
        detail="Downloading and parsing document",
        current_step=1,
    )

    session = _get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")

        # Update status
        contract.status = "parsing"
        session.commit()

        # Download from MinIO
        file_bytes = download_file(contract.file_url)
        logger.info(
            "Downloaded %d bytes for contract %s",
            len(file_bytes),
            contract_id,
        )

        # Parse document
        raw_text = parse_document(file_bytes, contract.file_name)

        # Save parsed text
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
        return {"contract_id": contract_id, "char_count": len(raw_text)}

    except Exception as exc:
        logger.exception("Failed to parse contract %s", contract_id)
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
            detail=str(exc),
            current_step=1,
        )
        raise self.retry(exc=exc) from exc
    finally:
        session.close()
