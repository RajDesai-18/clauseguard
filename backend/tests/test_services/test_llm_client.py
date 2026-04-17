"""Tests for the LLM client with circuit breaker and fallback."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services import llm_client as llm_module
from app.services.llm_client import call_llm, call_llm_json


def _make_completion_response(content: str) -> MagicMock:
    """Build a mock LiteLLM completion response."""
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the circuit breaker to closed state between tests."""
    llm_module.llm_circuit_breaker.close()
    yield
    llm_module.llm_circuit_breaker.close()


def test_call_llm_success_uses_primary():
    """Happy path: primary succeeds and returns its content."""
    mock_response = _make_completion_response("primary response")

    with patch.object(llm_module, "completion", return_value=mock_response) as mock_completion:
        result = call_llm([{"role": "user", "content": "hi"}])

    assert result == "primary response"
    assert mock_completion.call_count == 1
    # Primary model was used
    assert mock_completion.call_args.kwargs["model"] == llm_module.settings.llm_primary_model


def test_call_llm_primary_exception_falls_back():
    """If primary raises, fallback should be called automatically."""
    primary_response = Exception("primary down")
    fallback_response = _make_completion_response("fallback response")

    with patch.object(
        llm_module,
        "completion",
        side_effect=[primary_response, fallback_response],
    ) as mock_completion:
        result = call_llm([{"role": "user", "content": "hi"}])

    assert result == "fallback response"
    assert mock_completion.call_count == 2
    # Second call used the fallback model
    second_call_model = mock_completion.call_args_list[1].kwargs["model"]
    assert second_call_model == llm_module.settings.llm_fallback_model


def test_call_llm_both_fail_raises():
    """If both primary and fallback fail, the error should propagate."""
    with (
        patch.object(
            llm_module,
            "completion",
            side_effect=[Exception("primary down"), Exception("fallback down")],
        ),
        pytest.raises(Exception, match="fallback down"),
    ):
        call_llm([{"role": "user", "content": "hi"}])


def test_circuit_breaker_opens_after_5_failures():
    """After 5 consecutive primary failures, circuit opens and fallback is used directly."""
    fallback_response = _make_completion_response("fallback after open")

    # First 5 calls fail on primary, each attempt also gets a fallback call
    # After that the breaker is open, so only fallback is called
    side_effects = []
    for _ in range(5):
        side_effects.append(Exception("primary down"))  # primary fails
        side_effects.append(fallback_response)  # fallback succeeds
    # 6th call: breaker open, goes straight to fallback
    side_effects.append(fallback_response)

    with patch.object(llm_module, "completion", side_effect=side_effects) as mock_completion:
        # Trip the breaker with 5 failing primary calls
        for _ in range(5):
            call_llm([{"role": "user", "content": "hi"}])

        # Circuit should now be open
        assert llm_module.llm_circuit_breaker.current_state == "open"

        # Next call should skip primary entirely and call fallback directly
        result = call_llm([{"role": "user", "content": "hi"}])

    assert result == "fallback after open"
    # Total calls: 5 primary + 5 fallback + 1 fallback-only = 11
    assert mock_completion.call_count == 11


def test_circuit_breaker_error_routes_to_fallback():
    """When breaker raises CircuitBreakerError, fallback is called."""
    fallback_response = _make_completion_response("fallback response")

    # Manually trip the breaker
    llm_module.llm_circuit_breaker.open()
    assert llm_module.llm_circuit_breaker.current_state == "open"

    with patch.object(llm_module, "completion", return_value=fallback_response) as mock_completion:
        result = call_llm([{"role": "user", "content": "hi"}])

    assert result == "fallback response"
    assert mock_completion.call_count == 1
    # Only the fallback model was used, primary was skipped
    assert mock_completion.call_args.kwargs["model"] == llm_module.settings.llm_fallback_model


def test_call_llm_json_parses_valid_json():
    """call_llm_json should parse the response content as JSON."""
    payload = {"risk_level": "yellow", "confidence": 0.8}
    mock_response = _make_completion_response(json.dumps(payload))

    with patch.object(llm_module, "completion", return_value=mock_response) as mock_completion:
        result = call_llm_json([{"role": "user", "content": "hi"}])

    assert result == payload
    # response_format should have been injected
    assert mock_completion.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_call_llm_json_raises_on_invalid_json():
    """Invalid JSON in the response should propagate a JSONDecodeError."""
    mock_response = _make_completion_response("this is not json")

    with (
        patch.object(llm_module, "completion", return_value=mock_response),
        pytest.raises(json.JSONDecodeError),
    ):
        call_llm_json([{"role": "user", "content": "hi"}])


def test_call_llm_passes_kwargs_to_completion():
    """Additional kwargs like temperature should be forwarded to LiteLLM."""
    mock_response = _make_completion_response("ok")

    with patch.object(llm_module, "completion", return_value=mock_response) as mock_completion:
        call_llm([{"role": "user", "content": "hi"}], temperature=0.2, max_tokens=500)

    kwargs = mock_completion.call_args.kwargs
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 500
