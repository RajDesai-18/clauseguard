"""Saga orchestrator: contract processing pipeline."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings
from app.core.storage import download_file
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.cache import get_cached_analysis, set_cached_analysis
from app.services.clause_analyzer import analyze_clause
from app.services.clause_splitter import split_clauses
from app.services.document_parser import parse_document
from app.services.embedding import generate_embeddings_batch
from app.services.progress import publish_progress_sync
from app.services.redline_generator import generate_redline
from app.services.semantic_cache import find_similar_clause

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous DB session for Celery tasks."""
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return Session(engine)


def _compute_overall_risk(clauses: list[dict]) -> str:
    """Compute overall contract risk from individual clause risks.

    Logic:
        - Any red clause -> overall high
        - 3+ yellow clauses -> overall high
        - Any yellow clause -> overall medium
        - All green -> overall low
    """
    red_count = sum(1 for c in clauses if c["risk_level"] == "red")
    yellow_count = sum(1 for c in clauses if c["risk_level"] == "yellow")

    if red_count > 0:
        return "high"
    if yellow_count >= 3:
        return "high"
    if yellow_count > 0:
        return "medium"
    return "low"


@celery_app.task(name="app.tasks.pipeline.run_pipeline", bind=True, max_retries=0)
def run_pipeline(self, contract_id: str) -> dict:
    """Orchestrate the full contract analysis pipeline.

    Steps:
        1. Parse document (extract text from PDF/DOCX)
        2. Split into clauses and classify (LLM)
        3. Analyze each clause for risk (LLM)
        4. Generate redlines for risky clauses (LLM)
        5. Generate embeddings and persist results
    """
    logger.info("Pipeline started for contract %s", contract_id)
    publish_progress_sync(
        contract_id,
        status="parsing",
        detail="Extracting text from document",
        current_step=1,
    )

    session = _get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")

        # -- Step 1: Parse document ------------------------------
        contract.status = "parsing"
        session.commit()

        file_bytes = download_file(contract.file_url)
        raw_text = parse_document(file_bytes, contract.file_name)

        contract.raw_text = raw_text
        session.commit()

        publish_progress_sync(
            contract_id,
            status="parsed",
            detail=f"Extracted {len(raw_text)} characters",
            current_step=1,
        )
        logger.info("Parsed contract %s: %d chars", contract_id, len(raw_text))

        # -- Step 2: Split into clauses --------------------------
        contract.status = "analyzing"
        session.commit()

        publish_progress_sync(
            contract_id,
            status="analyzing",
            detail="Splitting contract into clauses",
            current_step=2,
        )

        split_result = split_clauses(raw_text)
        contract_type = split_result.get("contract_type", "other")
        summary = split_result.get("summary", "")
        raw_clauses = split_result.get("clauses", [])

        contract.contract_type = contract_type
        contract.summary = summary
        session.commit()

        logger.info(
            "Contract %s: type=%s, %d clauses found",
            contract_id,
            contract_type,
            len(raw_clauses),
        )

        # -- Step 3: Analyze each clause -------------------------
        publish_progress_sync(
            contract_id,
            status="scoring",
            detail=f"Analyzing {len(raw_clauses)} clauses",
            current_step=3,
        )
        contract.status = "scoring"
        session.commit()

        analyzed_clauses = []
        for i, raw_clause in enumerate(raw_clauses, 1):
            clause_text = raw_clause.get("original_text", "")
            clause_type = raw_clause.get("clause_type", "unknown")
            position = raw_clause.get("position", i)

            publish_progress_sync(
                contract_id,
                status="scoring",
                detail=f"Analyzing clause {i}/{len(raw_clauses)}: {clause_type}",
                current_step=3,
            )

            # Layer 1: Check Redis hash cache (exact match)
            analysis = get_cached_analysis(clause_text, contract_type)
            if analysis is not None:
                logger.info("Redis cache hit for clause %d (%s)", i, clause_type)
            else:
                # Layer 2: Check pgvector semantic cache (similar match)
                analysis = find_similar_clause(clause_text)
                if analysis is not None:
                    logger.info("Semantic cache hit for clause %d (%s)", i, clause_type)
                    # Store in Redis so next exact match is instant
                    set_cached_analysis(clause_text, contract_type, analysis)
                else:
                    # Layer 3: Call LLM
                    try:
                        analysis = analyze_clause(clause_text, clause_type, contract_type)
                        set_cached_analysis(clause_text, contract_type, analysis)
                    except Exception:
                        logger.exception(
                            "Failed to analyze clause %d (%s), defaulting to yellow",
                            i,
                            clause_type,
                        )
                        analysis = {
                            "risk_level": "yellow",
                            "confidence": 0.0,
                            "explanation": "Analysis failed. Manual review recommended.",
                            "market_comparison": "Unable to compare due to analysis error.",
                        }

            analyzed_clauses.append(
                {
                    "original_text": clause_text,
                    "clause_type": clause_type,
                    "position": position,
                    **analysis,
                }
            )

        # -- Step 4: Generate redlines for risky clauses ---------
        publish_progress_sync(
            contract_id,
            status="scoring",
            detail="Generating suggested revisions for risky clauses",
            current_step=4,
        )

        for clause_data in analyzed_clauses:
            if clause_data["risk_level"] in ("yellow", "red"):
                try:
                    redline = generate_redline(
                        clause_text=clause_data["original_text"],
                        clause_type=clause_data["clause_type"],
                        contract_type=contract_type,
                        risk_level=clause_data["risk_level"],
                        explanation=clause_data["explanation"],
                    )
                    clause_data["suggested_redline"] = redline
                except Exception:
                    logger.exception(
                        "Failed to generate redline for clause '%s'",
                        clause_data["clause_type"],
                    )
                    clause_data["suggested_redline"] = None
            else:
                clause_data["suggested_redline"] = None

        # -- Step 5: Generate embeddings, persist, finalize ------
        publish_progress_sync(
            contract_id,
            status="complete",
            detail="Generating embeddings and saving results",
            current_step=5,
        )

        # Batch-generate embeddings for all clause texts
        clause_texts = [c["original_text"] for c in analyzed_clauses]
        try:
            embeddings = generate_embeddings_batch(clause_texts)
            logger.info(
                "Generated %d embeddings for contract %s",
                len(embeddings),
                contract_id,
            )
        except Exception:
            logger.exception(
                "Failed to generate embeddings for contract %s, continuing without",
                contract_id,
            )
            embeddings = [None] * len(analyzed_clauses)

        for clause_data, embedding in zip(analyzed_clauses, embeddings, strict=True):
            clause = Clause(
                contract_id=contract.id,
                clause_type=clause_data["clause_type"],
                original_text=clause_data["original_text"],
                risk_level=clause_data["risk_level"],
                explanation=clause_data["explanation"],
                market_comparison=clause_data.get("market_comparison"),
                suggested_redline=clause_data.get("suggested_redline"),
                position=clause_data["position"],
                confidence=clause_data.get("confidence", 0.0),
                embedding=embedding,
            )
            session.add(clause)

        contract.clause_count = len(analyzed_clauses)
        contract.overall_risk = _compute_overall_risk(analyzed_clauses)
        contract.status = "complete"
        contract.analyzed_at = datetime.now(UTC)
        session.commit()

        publish_progress_sync(
            contract_id,
            status="complete",
            detail=(
                f"Analysis complete: {len(analyzed_clauses)} clauses, "
                f"overall risk: {contract.overall_risk}"
            ),
            current_step=5,
        )

        logger.info(
            "Pipeline complete for contract %s: %d clauses, risk=%s",
            contract_id,
            len(analyzed_clauses),
            contract.overall_risk,
        )

        return {
            "contract_id": contract_id,
            "status": "complete",
            "contract_type": contract_type,
            "clause_count": len(analyzed_clauses),
            "overall_risk": contract.overall_risk,
        }

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
            contract_id,
            status="failed",
            detail="Pipeline failed",
            current_step=0,
        )
        raise
    finally:
        session.close()
