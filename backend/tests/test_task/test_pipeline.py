"""Pipeline orchestration tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.celery_app import ping
from app.tasks import pipeline as pipeline_module
from app.tasks.pipeline import _compute_overall_risk, run_pipeline

# ---------------------------------------------------------------
# Ping task (smoke test for Celery app wiring)
# ---------------------------------------------------------------


def test_ping_task():
    """Ping task should return pong."""
    result = ping()
    assert result == "pong"


# ---------------------------------------------------------------
# Overall risk computation (pure logic)
# ---------------------------------------------------------------


def test_overall_risk_all_green_is_low():
    """All green clauses should produce low overall risk."""
    clauses = [{"risk_level": "green"}] * 5
    assert _compute_overall_risk(clauses) == "low"


def test_overall_risk_any_red_is_high():
    """A single red clause should make overall risk high."""
    clauses = [
        {"risk_level": "green"},
        {"risk_level": "green"},
        {"risk_level": "red"},
    ]
    assert _compute_overall_risk(clauses) == "high"


def test_overall_risk_three_or_more_yellows_is_high():
    """3+ yellow clauses with no red should produce high risk."""
    clauses = [{"risk_level": "yellow"}] * 3 + [{"risk_level": "green"}]
    assert _compute_overall_risk(clauses) == "high"


def test_overall_risk_one_or_two_yellows_is_medium():
    """1-2 yellow clauses with no red should produce medium risk."""
    clauses_one = [{"risk_level": "yellow"}, {"risk_level": "green"}]
    clauses_two = [{"risk_level": "yellow"}, {"risk_level": "yellow"}, {"risk_level": "green"}]
    assert _compute_overall_risk(clauses_one) == "medium"
    assert _compute_overall_risk(clauses_two) == "medium"


def test_overall_risk_empty_clauses_is_low():
    """No clauses should produce low risk (vacuously)."""
    assert _compute_overall_risk([]) == "low"


def test_overall_risk_red_dominates_yellows():
    """A red clause should always produce high risk, regardless of yellow count."""
    clauses = [{"risk_level": "yellow"}] * 5 + [{"risk_level": "red"}]
    assert _compute_overall_risk(clauses) == "high"


# ---------------------------------------------------------------
# Three-layer cache routing
# ---------------------------------------------------------------


@pytest.fixture
def mock_contract():
    """Build a mock Contract model instance."""
    contract = MagicMock()
    contract.id = uuid.uuid4()
    contract.file_url = "contracts/test.pdf"
    contract.file_name = "test.pdf"
    contract.contract_type = None
    contract.raw_text = None
    contract.status = "queued"
    return contract


@pytest.fixture
def mock_all_pipeline_deps(mock_contract):
    """Patch every external dependency the pipeline calls.

    Returns a dict of mocks so individual tests can tune behavior
    and assert against specific calls.
    """
    session = MagicMock()
    session.get.return_value = mock_contract

    patches = {
        "session": patch.object(pipeline_module, "_get_sync_session", return_value=session),
        "download": patch.object(pipeline_module, "download_file", return_value=b"fake bytes"),
        "parse": patch.object(
            pipeline_module, "parse_document", return_value="Full contract text."
        ),
        "split": patch.object(
            pipeline_module,
            "split_clauses",
            return_value={
                "contract_type": "nda",
                "summary": "An NDA between two parties.",
                "clauses": [
                    {
                        "original_text": "Clause one text.",
                        "clause_type": "confidentiality",
                        "position": 1,
                    },
                ],
            },
        ),
        "redis_cache_get": patch.object(pipeline_module, "get_cached_analysis", return_value=None),
        "redis_cache_set": patch.object(pipeline_module, "set_cached_analysis"),
        "semantic_cache": patch.object(pipeline_module, "find_similar_clause", return_value=None),
        "analyze": patch.object(
            pipeline_module,
            "analyze_clause",
            return_value={
                "risk_level": "green",
                "confidence": 0.9,
                "explanation": "Standard clause.",
                "market_comparison": "Matches market.",
            },
        ),
        "redline": patch.object(
            pipeline_module, "generate_redline", return_value="Suggested revision."
        ),
        "embed": patch.object(
            pipeline_module,
            "generate_embeddings_batch",
            return_value=[[0.1] * 1536],
        ),
        "publish": patch.object(pipeline_module, "publish_progress_sync"),
    }

    started = {name: p.start() for name, p in patches.items()}
    started["_contract"] = mock_contract
    started["_session"] = session

    yield started

    for p in patches.values():
        p.stop()


def test_pipeline_happy_path_completes(mock_all_pipeline_deps):
    """Pipeline should run end to end and return a completion dict."""
    contract_id = str(mock_all_pipeline_deps["_contract"].id)

    result = run_pipeline(contract_id)  # type: ignore

    assert result["status"] == "complete"
    assert result["contract_type"] == "nda"
    assert result["clause_count"] == 1
    assert result["overall_risk"] == "low"  # single green clause


def test_pipeline_redis_cache_hit_skips_semantic_and_llm(mock_all_pipeline_deps):
    """When Redis cache hits, semantic cache and LLM analyzer should NOT be called."""
    cached = {
        "risk_level": "green",
        "confidence": 0.95,
        "explanation": "Cached.",
        "market_comparison": "Cached comparison.",
    }
    mock_all_pipeline_deps["redis_cache_get"].return_value = cached

    run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    mock_all_pipeline_deps["redis_cache_get"].assert_called()
    mock_all_pipeline_deps["semantic_cache"].assert_not_called()
    mock_all_pipeline_deps["analyze"].assert_not_called()


def test_pipeline_semantic_cache_hit_skips_llm(mock_all_pipeline_deps):
    """When Redis misses but semantic cache hits, LLM analyzer should NOT be called."""
    cached = {
        "risk_level": "yellow",
        "confidence": 0.88,
        "explanation": "Semantic match.",
        "market_comparison": "Similar clauses found.",
    }
    mock_all_pipeline_deps["redis_cache_get"].return_value = None
    mock_all_pipeline_deps["semantic_cache"].return_value = cached

    run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    mock_all_pipeline_deps["redis_cache_get"].assert_called()
    mock_all_pipeline_deps["semantic_cache"].assert_called()
    mock_all_pipeline_deps["analyze"].assert_not_called()
    # Semantic hit should populate the Redis cache for next time
    mock_all_pipeline_deps["redis_cache_set"].assert_called()


def test_pipeline_cache_miss_calls_llm(mock_all_pipeline_deps):
    """When both caches miss, the LLM analyzer should be called."""
    mock_all_pipeline_deps["redis_cache_get"].return_value = None
    mock_all_pipeline_deps["semantic_cache"].return_value = None

    run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    mock_all_pipeline_deps["analyze"].assert_called_once()
    # LLM result should be cached for next time
    mock_all_pipeline_deps["redis_cache_set"].assert_called()


def test_pipeline_llm_failure_defaults_to_yellow(mock_all_pipeline_deps):
    """If the LLM analyzer raises, the clause should default to yellow."""
    mock_all_pipeline_deps["redis_cache_get"].return_value = None
    mock_all_pipeline_deps["semantic_cache"].return_value = None
    mock_all_pipeline_deps["analyze"].side_effect = RuntimeError("llm down")

    result = run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    # One yellow clause = medium overall risk
    assert result["overall_risk"] == "medium"


def test_pipeline_redlines_only_for_risky_clauses(mock_all_pipeline_deps):
    """Redline generation should only be invoked for yellow/red clauses."""
    # Green clause from default analyze mock
    run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore
    mock_all_pipeline_deps["redline"].assert_not_called()


def test_pipeline_redlines_called_for_yellow(mock_all_pipeline_deps):
    """A yellow clause should trigger redline generation."""
    mock_all_pipeline_deps["analyze"].return_value = {
        "risk_level": "yellow",
        "confidence": 0.8,
        "explanation": "Somewhat risky.",
        "market_comparison": "One-sided.",
    }

    run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    mock_all_pipeline_deps["redline"].assert_called_once()


def test_pipeline_contract_not_found_raises(mock_all_pipeline_deps):
    """When the contract doesn't exist, the task should raise."""
    mock_all_pipeline_deps["_session"].get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        run_pipeline(str(uuid.uuid4()))  # type: ignore


def test_pipeline_failure_sets_status_to_failed(mock_all_pipeline_deps):
    """When a step crashes, the contract status should be updated to failed."""
    mock_all_pipeline_deps["parse"].side_effect = RuntimeError("parse failed")

    with pytest.raises(RuntimeError, match="parse failed"):
        run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    # Final status update should have set it to "failed"
    assert mock_all_pipeline_deps["_contract"].status == "failed"


def test_pipeline_embedding_failure_does_not_crash(mock_all_pipeline_deps):
    """If embedding generation fails, pipeline should continue with None embeddings."""
    mock_all_pipeline_deps["embed"].side_effect = RuntimeError("openai down")

    result = run_pipeline(str(mock_all_pipeline_deps["_contract"].id))  # type: ignore

    assert result["status"] == "complete"
