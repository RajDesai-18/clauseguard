"""End-to-end saga test.

Runs the full pipeline (parse -> classify -> analyze fan-out -> score
-> redline fan-out -> finalize) in Celery eager mode against a real
database. LLM, embedding, and storage calls are mocked.

This is the integration test that catches saga wiring regressions:
chain construction, dispatcher task behavior, chord callbacks,
state passing between stages.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.clause import Clause
from app.models.contract import Contract


@pytest.fixture
def fake_pipeline_split_response() -> dict:
    """Splitter response with a mix of clause types so the saga
    has variety to work with: one likely-green and one likely-yellow.
    """
    return {
        "contract_type": "nda",
        "summary": "An end-to-end test NDA.",
        "clauses": [
            {
                "clause_type": "confidentiality",
                "original_text": (
                    "Each party agrees to maintain strict confidentiality "
                    "of all proprietary information shared during this agreement."
                ),
                "position": 1,
            },
            {
                "clause_type": "non_compete",
                "original_text": (
                    "Recipient may not engage in any competitive business "
                    "for a period of five years following termination."
                ),
                "position": 2,
            },
            {
                "clause_type": "termination",
                "original_text": (
                    "This agreement may be terminated by either party with "
                    "thirty days written notice."
                ),
                "position": 3,
            },
        ],
    }


def _analyze_response_for(clause_type: str) -> dict:
    """Return a deterministic analysis based on clause type.

    Confidentiality and termination are green, non_compete is red.
    Mirrors what the real LLM would likely return for these texts.
    """
    if clause_type == "non_compete":
        return {
            "risk_level": "red",
            "confidence": 0.93,
            "explanation": "Five-year non-compete is unusually broad.",
            "market_comparison": "Standard non-competes run 12 months at most.",
        }
    return {
        "risk_level": "green",
        "confidence": 0.95,
        "explanation": "Standard, market-typical language.",
        "market_comparison": "Matches common NDA templates.",
    }


def test_saga_runs_end_to_end(
    sync_session: Session,
    db_contract: Contract,
    fake_pipeline_split_response: dict,
):
    """Full pipeline should take a parsed contract to status=complete.

    Asserts on DB state at the end:
    - Contract is marked complete
    - All clauses persisted with risk fields
    - Risky clauses got redlines, green ones didn't
    - Embeddings populated
    - Overall risk computed correctly
    """
    from app.tasks.pipeline import run_pipeline

    fake_embedding = [0.1] * 1536

    # Side effect for analyze_clause: look at the clause_type kwarg
    # and return the appropriate canned analysis.
    def analyze_side_effect(clause_text, clause_type, contract_type):
        return _analyze_response_for(clause_type)

    with (
        # Splitter (called by classify_clauses_task)
        patch(
            "app.tasks.classify.split_clauses",
            return_value=fake_pipeline_split_response,
        ),
        # Caches all miss so analyze_clause is invoked for every clause
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch("app.tasks.score.find_similar_clause", return_value=None),
        patch("app.tasks.score.set_cached_analysis"),
        # Analyzer returns deterministic risk per clause type
        patch(
            "app.tasks.score.analyze_clause",
            side_effect=analyze_side_effect,
        ),
        # Redline generator returns canned text
        patch(
            "app.tasks.redline.generate_redline",
            return_value="Suggested revision text.",
        ),
        # Embedding batch returns one vector per input
        patch(
            "app.tasks.finalize.generate_embeddings_batch",
            side_effect=lambda texts: [fake_embedding] * len(texts),
        ),
        # Skip the parse step's MinIO download and PDF parsing.
        # The contract fixture already has raw_text; classify reads it
        # directly. But run_pipeline starts from parse, so we need to
        # let parse "succeed" against a contract that's already parsed.
        patch(
            "app.tasks.parse.download_file",
            return_value=b"fake pdf bytes",
        ),
        patch(
            "app.tasks.parse.parse_document",
            return_value=db_contract.raw_text,
        ),
    ):
        run_pipeline(str(db_contract.id))

    # In eager mode, run_pipeline returns once the chain head completes,
    # but dispatchers fire chords asynchronously even in eager mode.
    # By the time apply_async returns inside the dispatcher, eager mode
    # has executed everything synchronously, so all DB writes are done.

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.status == "complete", f"Expected status 'complete', got '{contract.status}'"
    assert contract.contract_type == "nda"
    assert contract.clause_count == 3
    assert contract.overall_risk == "high"  # one red clause
    assert contract.analyzed_at is not None

    clauses = (
        sync_session.query(Clause)
        .filter(Clause.contract_id == db_contract.id)
        .order_by(Clause.position)
        .all()
    )
    assert len(clauses) == 3

    # Clause 1: confidentiality, green, no redline
    assert clauses[0].clause_type == "confidentiality"
    assert clauses[0].risk_level == "green"
    assert clauses[0].confidence == pytest.approx(0.95)
    assert clauses[0].suggested_redline is None
    assert clauses[0].embedding is not None

    # Clause 2: non_compete, red, has redline
    assert clauses[1].clause_type == "non_compete"
    assert clauses[1].risk_level == "red"
    assert clauses[1].suggested_redline == "Suggested revision text."
    assert clauses[1].embedding is not None

    # Clause 3: termination, green, no redline
    assert clauses[2].clause_type == "termination"
    assert clauses[2].risk_level == "green"
    assert clauses[2].suggested_redline is None
    assert clauses[2].embedding is not None


def test_saga_with_no_risky_clauses_skips_redline_chord(
    sync_session: Session,
    db_contract: Contract,
    fake_pipeline_split_response: dict,
):
    """When all clauses are green, the redline chord should be skipped
    and the pipeline should still reach status=complete.

    This exercises the dispatch_redlines_task short-circuit branch.
    """
    from app.tasks.pipeline import run_pipeline

    all_green = {
        "risk_level": "green",
        "confidence": 0.95,
        "explanation": "Standard, market-typical language.",
        "market_comparison": "Matches common NDA templates.",
    }
    fake_embedding = [0.1] * 1536

    with (
        patch(
            "app.tasks.classify.split_clauses",
            return_value=fake_pipeline_split_response,
        ),
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch("app.tasks.score.find_similar_clause", return_value=None),
        patch("app.tasks.score.set_cached_analysis"),
        patch("app.tasks.score.analyze_clause", return_value=all_green),
        patch("app.tasks.redline.generate_redline") as mock_redline,
        patch(
            "app.tasks.finalize.generate_embeddings_batch",
            side_effect=lambda texts: [fake_embedding] * len(texts),
        ),
        patch(
            "app.tasks.parse.download_file",
            return_value=b"fake pdf bytes",
        ),
        patch(
            "app.tasks.parse.parse_document",
            return_value=db_contract.raw_text,
        ),
    ):
        run_pipeline(str(db_contract.id))

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.status == "complete"
    assert contract.overall_risk == "low"

    # generate_redline should not have been called for any clause
    mock_redline.assert_not_called()


def test_saga_status_transitions_through_all_stages(
    sync_session: Session,
    db_contract: Contract,
    fake_pipeline_split_response: dict,
):
    """The contract status field should reach 'complete' from a 'parsed' start.

    We can't observe intermediate states reliably in eager mode (everything
    runs synchronously in one Python call), but we can assert the final state
    and that analyzed_at was set, which only happens in score_contract_task.
    """
    from app.tasks.pipeline import run_pipeline

    fake_embedding = [0.1] * 1536

    with (
        patch(
            "app.tasks.classify.split_clauses",
            return_value=fake_pipeline_split_response,
        ),
        patch("app.tasks.score.get_cached_analysis", return_value=None),
        patch("app.tasks.score.find_similar_clause", return_value=None),
        patch("app.tasks.score.set_cached_analysis"),
        patch(
            "app.tasks.score.analyze_clause",
            side_effect=lambda *a, **kw: _analyze_response_for(a[1]),
        ),
        patch(
            "app.tasks.redline.generate_redline",
            return_value="redline",
        ),
        patch(
            "app.tasks.finalize.generate_embeddings_batch",
            side_effect=lambda texts: [fake_embedding] * len(texts),
        ),
        patch(
            "app.tasks.parse.download_file",
            return_value=b"fake pdf bytes",
        ),
        patch(
            "app.tasks.parse.parse_document",
            return_value=db_contract.raw_text,
        ),
    ):
        run_pipeline(str(db_contract.id))

    sync_session.expire_all()
    contract = sync_session.get(Contract, db_contract.id)
    assert contract is not None
    assert contract.status == "complete"
    # analyzed_at is only set by score_contract_task, so its presence
    # proves we got past the score stage.
    assert contract.analyzed_at is not None
