"""Per-task integration tests for the saga.

Each test exercises one task in isolation with real DB writes and
mocked LLM/embedding calls. The fixtures from conftest provide the
DB session, persisted user, and contract.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.models.clause import Clause
from app.models.contract import Contract

# ---------------------------------------------------------------
# classify_clauses_task
# ---------------------------------------------------------------


def test_classify_persists_clauses_with_null_risk(
    sync_session: Session,
    db_contract: Contract,
    fake_split_response: dict,
):
    """classify_clauses_task should persist clauses with risk fields null."""
    from app.tasks.classify import classify_clauses_task

    with patch(
        "app.tasks.classify.split_clauses",
        return_value=fake_split_response,
    ):
        result = classify_clauses_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    assert result["contract_id"] == str(db_contract.id)
    assert result["contract_type"] == "nda"
    assert result["clause_count"] == 2

    sync_session.expire_all()
    clauses = (
        sync_session.query(Clause)
        .filter(Clause.contract_id == db_contract.id)
        .order_by(Clause.position)
        .all()
    )
    assert len(clauses) == 2
    assert clauses[0].clause_type == "confidentiality"
    assert clauses[0].risk_level is None
    assert clauses[0].explanation is None
    assert clauses[1].clause_type == "termination"


def test_classify_updates_contract_metadata(
    sync_session: Session,
    db_contract: Contract,
    fake_split_response: dict,
):
    """classify should set contract_type, summary, clause_count, and status."""
    from app.tasks.classify import classify_clauses_task

    with patch(
        "app.tasks.classify.split_clauses",
        return_value=fake_split_response,
    ):
        classify_clauses_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.contract_type == "nda"
    assert contract.summary == "A short test NDA."
    assert contract.clause_count == 2
    assert contract.status == "analyzing"


def test_classify_raises_on_missing_raw_text(
    sync_session: Session,
    db_contract: Contract,
):
    """classify should fail if the parse step didn't run."""
    from app.tasks.classify import classify_clauses_task

    db_contract.raw_text = None
    sync_session.commit()

    with pytest.raises(Exception, match="raw_text"):
        classify_clauses_task.run({"contract_id": str(db_contract.id)})  # type: ignore


def test_classify_raises_on_empty_clauses(
    sync_session: Session,
    db_contract: Contract,
):
    """classify should fail if the LLM returns zero clauses."""
    from app.tasks.classify import classify_clauses_task

    empty_response = {"contract_type": "nda", "summary": "", "clauses": []}
    with (
        patch("app.tasks.classify.split_clauses", return_value=empty_response),
        pytest.raises(Exception, match="zero clauses"),
    ):
        classify_clauses_task.run({"contract_id": str(db_contract.id)})  # type: ignore


# ---------------------------------------------------------------
# analyze_one_clause_task
# ---------------------------------------------------------------


@pytest.fixture
def db_clause(sync_session: Session, db_contract: Contract) -> Clause:
    """A persisted unanalyzed clause attached to db_contract."""
    clause = Clause(
        contract_id=db_contract.id,
        clause_type="confidentiality",
        original_text="Each party agrees to maintain confidentiality.",
        position=1,
    )
    sync_session.add(clause)
    sync_session.commit()
    sync_session.refresh(clause)
    return clause


def test_analyze_persists_risk_fields(
    sync_session: Session,
    db_clause: Clause,
    fake_analysis_yellow: dict,
):
    """analyze_one_clause_task should populate risk_level, explanation, etc."""
    from app.tasks.score import analyze_one_clause_task

    with (
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch("app.tasks.score.find_similar_clause", return_value=None),
        patch("app.tasks.score.analyze_clause", return_value=fake_analysis_yellow),
        patch("app.tasks.score.set_cached_analysis"),
    ):
        result = analyze_one_clause_task.run(str(db_clause.id))  # type: ignore

    assert result["risk_level"] == "yellow"
    assert result["cache_source"] == "llm"

    sync_session.expire_all()
    clause = sync_session.get(Clause, db_clause.id)
    assert clause is not None
    assert clause.risk_level == "yellow"
    assert clause.confidence == pytest.approx(0.85)
    assert clause.explanation == "This clause is somewhat one-sided."
    assert clause.market_comparison == "Standard clauses are more balanced."


def test_analyze_uses_redis_cache_first(
    sync_session: Session,
    db_clause: Clause,
    fake_analysis_yellow: dict,
):
    """When Redis cache hits, semantic and LLM should not be called."""
    from app.tasks.score import analyze_one_clause_task

    with (
        patch("app.tasks.score.get_cached_analysis", return_value=fake_analysis_yellow),
        patch("app.tasks.score.find_similar_clause") as mock_semantic,
        patch("app.tasks.score.analyze_clause") as mock_llm,
        patch("app.tasks.score.set_cached_analysis"),
    ):
        result = analyze_one_clause_task.run(str(db_clause.id))  # type: ignore

    assert result["cache_source"] == "redis"
    mock_semantic.assert_not_called()
    mock_llm.assert_not_called()


def test_analyze_uses_semantic_cache_when_redis_misses(
    sync_session: Session,
    db_clause: Clause,
    fake_analysis_yellow: dict,
):
    """When Redis misses but semantic hits, LLM should not be called."""
    from app.tasks.score import analyze_one_clause_task

    with (
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch(
            "app.tasks.score.find_similar_clause",
            return_value=fake_analysis_yellow,
        ),
        patch("app.tasks.score.analyze_clause") as mock_llm,
        patch("app.tasks.score.set_cached_analysis") as mock_set,
    ):
        result = analyze_one_clause_task.run(str(db_clause.id))  # type: ignore

    assert result["cache_source"] == "semantic"
    mock_llm.assert_not_called()
    # Semantic hit should backfill Redis
    mock_set.assert_called_once()


def test_analyze_falls_back_to_yellow_on_llm_failure(
    sync_session: Session,
    db_clause: Clause,
):
    """If both caches miss and the LLM fails, the clause should become yellow."""
    from app.tasks.score import analyze_one_clause_task

    with (
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch("app.tasks.score.find_similar_clause", return_value=None),
        patch(
            "app.tasks.score.analyze_clause",
            side_effect=RuntimeError("llm down"),
        ),
        patch("app.tasks.score.set_cached_analysis"),
    ):
        result = analyze_one_clause_task.run(str(db_clause.id))  # type: ignore

    assert result["risk_level"] == "yellow"
    assert result["cache_source"] == "fallback"

    sync_session.expire_all()
    clause = sync_session.get(Clause, db_clause.id)
    assert clause is not None
    assert clause.risk_level == "yellow"
    assert clause.confidence == 0.0
    assert "Analysis failed" in (clause.explanation or "")


# ---------------------------------------------------------------
# score_contract_task
# ---------------------------------------------------------------


def test_score_computes_overall_risk_from_db(
    sync_session: Session,
    db_contract: Contract,
):
    """score_contract_task should read risk levels from clauses and compute overall risk."""
    from app.tasks.score import score_contract_task

    # Insert three clauses with mixed risk levels
    for i, risk in enumerate(["green", "yellow", "red"], 1):
        sync_session.add(
            Clause(
                contract_id=db_contract.id,
                clause_type=f"clause_{i}",
                original_text=f"Clause {i} text.",
                position=i,
                risk_level=risk,
                confidence=0.9,
                explanation=f"Explanation {i}",
            )
        )
    sync_session.commit()

    result = score_contract_task.run([], str(db_contract.id))  # type: ignore

    assert result["overall_risk"] == "high"  # any red -> high
    assert result["clause_count"] == 3

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.overall_risk == "high"
    assert contract.analyzed_at is not None


def test_score_treats_unanalyzed_clauses_as_yellow(
    sync_session: Session,
    db_contract: Contract,
):
    """If some clauses have null risk_level, treat them as yellow rather than crashing."""
    from app.tasks.score import score_contract_task

    sync_session.add(
        Clause(
            contract_id=db_contract.id,
            clause_type="green_one",
            original_text="green clause",
            position=1,
            risk_level="green",
            confidence=0.9,
        )
    )
    sync_session.add(
        Clause(
            contract_id=db_contract.id,
            clause_type="unanalyzed",
            original_text="never analyzed",
            position=2,
            risk_level=None,
        )
    )
    sync_session.commit()

    result = score_contract_task.run([], str(db_contract.id))  # type: ignore

    # 1 yellow (the unanalyzed) + 1 green = medium
    assert result["overall_risk"] == "medium"


# ---------------------------------------------------------------
# finalize_contract_task
# ---------------------------------------------------------------


def test_finalize_marks_contract_complete(
    sync_session: Session,
    db_contract: Contract,
):
    """finalize_contract_task should set status=complete and add embeddings."""
    from app.tasks.finalize import finalize_contract_task

    sync_session.add(
        Clause(
            contract_id=db_contract.id,
            clause_type="confidentiality",
            original_text="confidentiality text",
            position=1,
            risk_level="green",
            confidence=0.95,
        )
    )
    db_contract.clause_count = 1
    db_contract.overall_risk = "low"
    sync_session.commit()

    fake_embedding = [0.1] * 1536
    with patch(
        "app.tasks.finalize.generate_embeddings_batch",
        return_value=[fake_embedding],
    ):
        result = finalize_contract_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    assert result["status"] == "complete"

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.status == "complete"

    clauses = sync_session.query(Clause).filter(Clause.contract_id == db_contract.id).all()
    assert clauses[0].embedding is not None


def test_finalize_continues_when_embeddings_fail(
    sync_session: Session,
    db_contract: Contract,
):
    """Embedding failure should not abort the pipeline; status still goes to complete."""
    from app.tasks.finalize import finalize_contract_task

    sync_session.add(
        Clause(
            contract_id=db_contract.id,
            clause_type="x",
            original_text="x",
            position=1,
            risk_level="green",
        )
    )
    sync_session.commit()

    with patch(
        "app.tasks.finalize.generate_embeddings_batch",
        side_effect=RuntimeError("openai down"),
    ):
        result = finalize_contract_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    assert result["status"] == "complete"

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.status == "complete"


def test_finalize_skips_already_embedded_clauses(
    sync_session: Session,
    db_contract: Contract,
):
    """On retry after partial success, finalize should not re-embed clauses."""
    from app.tasks.finalize import finalize_contract_task

    existing_vec = [0.5] * 1536
    sync_session.add(
        Clause(
            contract_id=db_contract.id,
            clause_type="x",
            original_text="x",
            position=1,
            risk_level="green",
            embedding=existing_vec,
        )
    )
    sync_session.commit()

    with patch("app.tasks.finalize.generate_embeddings_batch") as mock_embed:
        finalize_contract_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    # No clauses needed embedding -> the function should not have been called
    mock_embed.assert_not_called()


# ---------------------------------------------------------------
# Sanity check: contract_id flows through task return values
# ---------------------------------------------------------------


def test_classify_return_shape_matches_dispatch_expectation(
    sync_session: Session,
    db_contract: Contract,
    fake_split_response: dict,
):
    """classify's return must contain contract_id for the dispatcher to pick up."""
    from app.tasks.classify import classify_clauses_task

    with patch(
        "app.tasks.classify.split_clauses",
        return_value=fake_split_response,
    ):
        result = classify_clauses_task.run({"contract_id": str(db_contract.id)})  # type: ignore

    # The dispatcher reads `contract_id` from this dict
    assert "contract_id" in result
    UUID(result["contract_id"])  # valid UUID format
