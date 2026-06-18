"""Step 3: Analyze each clause for risk (fan-out) and compute overall risk."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.celery_app import celery_app
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.cache import get_cached_analysis, set_cached_analysis
from app.services.clause_analyzer import analyze_clause
from app.services.progress import publish_progress_sync
from app.services.semantic_cache import find_similar_clause
from app.tasks._session import get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.score.analyze_one_clause_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    soft_time_limit=60,
    time_limit=90,
)
def analyze_one_clause_task(self, clause_id: str) -> dict:
    """Analyze a single clause for risk.

    Walks the cache hierarchy:
        1. Redis exact-match cache (clause_text + contract_type hash)
        2. pgvector semantic cache (similarity >= 0.92)
        3. LLM via analyze_clause (which itself queries template_matcher)

    Persists the analysis fields back to the Clause row.

    Args:
        clause_id: UUID of the clause to analyze.

    Returns:
        Dict with clause_id and risk_level (small payload for chord callback).
    """
    logger.info("Analyzing clause %s", clause_id)

    session = get_sync_session()
    try:
        clause = session.get(Clause, uuid.UUID(clause_id))
        if clause is None:
            raise ValueError(f"Clause {clause_id} not found")

        contract = session.get(Contract, clause.contract_id)
        if contract is None:
            raise ValueError(f"Contract {clause.contract_id} not found")

        contract_id_str = str(contract.id)
        contract_type = contract.contract_type or "other"
        clause_text = clause.original_text
        clause_type = clause.clause_type

        # Layer 1: Redis exact-match cache
        analysis = get_cached_analysis(clause_text, contract_type)
        cache_source = "redis" if analysis is not None else None

        # Layer 2: pgvector semantic cache
        if analysis is None:
            analysis = find_similar_clause(clause_text)
            if analysis is not None:
                cache_source = "semantic"
                # Backfill Redis so next exact match is instant
                set_cached_analysis(clause_text, contract_type, analysis)

        # Layer 3: LLM
        if analysis is None:
            try:
                analysis = analyze_clause(clause_text, clause_type, contract_type)
                cache_source = "llm"
                set_cached_analysis(clause_text, contract_type, analysis)
            except Exception:
                logger.exception(
                    "LLM analysis failed for clause %s (%s); using fallback",
                    clause_id,
                    clause_type,
                )
                analysis = {
                    "risk_level": "yellow",
                    "confidence": 0.0,
                    "explanation": "Analysis failed. Manual review recommended.",
                    "market_comparison": ("Unable to compare due to analysis error."),
                }
                cache_source = "fallback"

        # Persist analysis back to the clause row
        clause.risk_level = analysis["risk_level"]
        clause.confidence = analysis.get("confidence", 0.0)
        clause.explanation = analysis.get("explanation")  # type: ignore
        clause.market_comparison = analysis.get("market_comparison")  # type: ignore
        session.commit()

        # Per-clause progress event (the orchestrator emits aggregate progress;
        # this is fine-grained for live UI updates)
        publish_progress_sync(
            contract_id_str,  # type: ignore
            status="scoring",
            detail=f"Analyzed clause: {clause_type} ({analysis['risk_level']})",
            current_step=3,
        )

        logger.info(
            "Analyzed clause %s (%s): risk=%s, source=%s",
            clause_id,
            clause_type,
            analysis["risk_level"],
            cache_source,
        )

        return {
            "clause_id": clause_id,
            "risk_level": analysis["risk_level"],
            "cache_source": cache_source,
        }

    except Exception:
        logger.exception("Failed to analyze clause %s", clause_id)
        # Don't mark the contract failed for a single clause failure;
        # the chord callback will see this in the results.
        # But we DO want the retry behavior, so re-raise.
        raise
    finally:
        session.close()


@celery_app.task(
    name="app.tasks.score.score_contract_task",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=2,
    soft_time_limit=30,
    time_limit=60,
)
def score_contract_task(self, _clause_results: list, contract_id: str) -> dict:
    """Compute overall contract risk after all clauses are analyzed.

    This task is the chord callback. The first argument is the list of
    per-clause analysis results from the group, but we don't use it
    directly; we re-read from the DB so we have authoritative state.

    Args:
        _clause_results: List of dicts from analyze_one_clause_task (unused).
        contract_id: UUID of the contract to score.

    Returns:
        Dict with contract_id and overall_risk for the next chain step.
    """
    logger.info("Computing overall risk for contract %s", contract_id)

    session = get_sync_session()
    try:
        contract = session.get(Contract, uuid.UUID(contract_id))
        if contract is None:
            raise ValueError(f"Contract {contract_id} not found")

        clauses = session.query(Clause).filter(Clause.contract_id == contract.id).all()
        if not clauses:
            raise ValueError(f"No clauses found for contract {contract_id}")

        risk_levels = [c.risk_level for c in clauses if c.risk_level is not None]
        unanalyzed = len(clauses) - len(risk_levels)
        if unanalyzed > 0:
            logger.warning(
                "Contract %s has %d unanalyzed clauses; treating them as yellow",
                contract_id,
                unanalyzed,
            )
            risk_levels.extend(["yellow"] * unanalyzed)

        overall_risk = _compute_overall_risk(risk_levels)
        contract.overall_risk = overall_risk
        contract.analyzed_at = datetime.now(UTC)
        session.commit()

        publish_progress_sync(
            contract_id,  # type: ignore
            status="scoring",
            detail=(
                f"Risk scoring complete: {len(clauses)} clauses, overall risk: {overall_risk}"
            ),
            current_step=3,
        )

        logger.info(
            "Scored contract %s: %d clauses, overall risk=%s",
            contract_id,
            len(clauses),
            overall_risk,
        )

        return {
            "contract_id": contract_id,
            "overall_risk": overall_risk,
            "clause_count": len(clauses),
        }

    except Exception as exc:
        logger.exception("Scoring failed for contract %s", contract_id)
        try:
            contract = session.get(Contract, uuid.UUID(contract_id))
            if contract is not None:
                contract.status = "failed"
                session.commit()
        except Exception:
            logger.exception("Failed to mark contract as failed")
        publish_progress_sync(
            contract_id,  # type: ignore
            status="failed",
            detail=f"Scoring failed: {exc}",
            current_step=3,
        )
        raise
    finally:
        session.close()


def _compute_overall_risk(risk_levels: list[str]) -> str:
    """Compute overall contract risk from individual clause risk levels.

    Logic:
        - Any red clause -> high
        - 3 or more yellow clauses -> high
        - Any yellow clause -> medium
        - All green -> low
    """
    red_count = sum(1 for r in risk_levels if r == "red")
    yellow_count = sum(1 for r in risk_levels if r == "yellow")

    if red_count > 0:
        return "high"
    if yellow_count >= 3:
        return "high"
    if yellow_count > 0:
        return "medium"
    return "low"
