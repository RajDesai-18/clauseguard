"""Tests for the clause analyzer orchestration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import clause_analyzer as analyzer_module
from app.services.clause_analyzer import analyze_clause


def _valid_llm_response(
    risk_level: str = "yellow",
    confidence: float = 0.85,
    explanation: str = "This clause is one-sided.",
    market_comparison: str = "Standard clauses are more balanced.",
) -> dict:
    """Build a valid LLM JSON response."""
    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "explanation": explanation,
        "market_comparison": market_comparison,
    }


def _template_match(similarity: float, clause_type: str = "indemnification") -> dict:
    """Build a template match dict."""
    return {
        "clause_type": clause_type,
        "standard_text": "Standard indemnification language goes here.",
        "similarity": similarity,
        "source": "internal",
    }


def test_returns_structured_analysis():
    """analyze_clause should return the validated LLM response."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", return_value=_valid_llm_response()),
    ):
        result = analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert result["risk_level"] == "yellow"
    assert result["confidence"] == 0.85
    assert result["explanation"] == "This clause is one-sided."
    assert result["market_comparison"] == "Standard clauses are more balanced."


def test_enriches_prompt_when_template_similarity_above_threshold():
    """Template with similarity >= 0.5 should be injected into the system prompt."""
    template = _template_match(similarity=0.75)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=template),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    # Inspect the system message passed to the LLM
    messages = mock_llm.call_args.args[0]
    system_content = messages[0]["content"]
    assert "MARKET-STANDARD REFERENCE" in system_content
    assert "Standard indemnification language goes here." in system_content
    assert "75%" in system_content  # similarity formatted as percent


def test_does_not_enrich_when_similarity_below_threshold():
    """Template with similarity < 0.5 should NOT be injected into the prompt."""
    template = _template_match(similarity=0.30)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=template),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    messages = mock_llm.call_args.args[0]
    system_content = messages[0]["content"]
    assert "MARKET-STANDARD REFERENCE" not in system_content


def test_does_not_enrich_when_no_template_found():
    """When find_nearest_template returns None, no enrichment should occur."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    messages = mock_llm.call_args.args[0]
    system_content = messages[0]["content"]
    assert "MARKET-STANDARD REFERENCE" not in system_content


def test_enrichment_at_exactly_threshold():
    """Similarity of exactly 0.5 should enrich the prompt (boundary case)."""
    template = _template_match(similarity=0.50)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=template),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    messages = mock_llm.call_args.args[0]
    system_content = messages[0]["content"]
    assert "MARKET-STANDARD REFERENCE" in system_content


@pytest.mark.parametrize("invalid_risk", ["blue", "critical", "", None, "GREEN", "high"])
def test_invalid_risk_level_defaults_to_yellow(invalid_risk):
    """Any risk_level outside {green, yellow, red} should default to yellow."""
    response = _valid_llm_response(risk_level=invalid_risk)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", return_value=response),
    ):
        result = analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert result["risk_level"] == "yellow"


@pytest.mark.parametrize("valid_risk", ["green", "yellow", "red"])
def test_valid_risk_levels_preserved(valid_risk):
    """Valid risk levels should pass through unchanged."""
    response = _valid_llm_response(risk_level=valid_risk)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", return_value=response),
    ):
        result = analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert result["risk_level"] == valid_risk


@pytest.mark.parametrize("invalid_confidence", [-0.1, 1.5, "high", None, "0.8"])
def test_invalid_confidence_defaults_to_half(invalid_confidence):
    """Confidence outside [0.0, 1.0] or wrong type should default to 0.5."""
    response = _valid_llm_response(confidence=invalid_confidence)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", return_value=response),
    ):
        result = analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert result["confidence"] == 0.5


@pytest.mark.parametrize("valid_confidence", [0.0, 0.5, 0.99, 1.0, 0])
def test_valid_confidence_preserved(valid_confidence):
    """Confidence in [0.0, 1.0] should pass through unchanged."""
    response = _valid_llm_response(confidence=valid_confidence)

    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", return_value=response),
    ):
        result = analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert result["confidence"] == valid_confidence


def test_user_message_contains_clause_text_and_type():
    """The user message sent to the LLM should include both clause type and text."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="The party agrees to indemnify without limit.",
            clause_type="indemnification",
            contract_type="nda",
        )

    messages = mock_llm.call_args.args[0]
    user_content = messages[1]["content"]
    assert "indemnification" in user_content
    assert "The party agrees to indemnify without limit." in user_content


def test_temperature_is_zero_for_deterministic_output():
    """The LLM call should pass temperature=0.0 for stable risk analysis."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )

    assert mock_llm.call_args.kwargs["temperature"] == 0.0


def test_contract_type_appears_in_system_prompt():
    """The contract_type should be formatted into the system prompt."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(
            analyzer_module, "call_llm_json", return_value=_valid_llm_response()
        ) as mock_llm,
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="msa",
        )

    messages = mock_llm.call_args.args[0]
    system_content = messages[0]["content"]
    assert "msa" in system_content


def test_llm_exception_propagates():
    """If the LLM call raises, the exception should propagate (not silently swallowed)."""
    with (
        patch.object(analyzer_module, "find_nearest_template", return_value=None),
        patch.object(analyzer_module, "call_llm_json", side_effect=RuntimeError("llm down")),
        pytest.raises(RuntimeError, match="llm down"),
    ):
        analyze_clause(
            clause_text="Some clause text.",
            clause_type="indemnification",
            contract_type="nda",
        )
