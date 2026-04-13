"""LLM client with circuit breaker and provider fallback."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import pybreaker
from litellm import completion

from app.core.config import settings

logger = logging.getLogger(__name__)

# Circuit breaker: opens after 5 consecutive failures, resets after 30s
llm_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="llm_primary",
)


def _cache_key(model: str, messages: list[dict], kwargs: dict) -> str:
    """Generate a deterministic cache key for an LLM request."""
    payload = json.dumps(
        {"model": model, "messages": messages, **kwargs},
        sort_keys=True,
    )
    return f"llm:cache:{hashlib.sha256(payload.encode()).hexdigest()}"


def _call_llm(
    model: str,
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Make a raw LiteLLM completion call.

    Args:
        model: LiteLLM model string (e.g. "gpt-4.1").
        messages: Chat messages in OpenAI format.
        **kwargs: Additional params (temperature, response_format, etc.).

    Returns:
        The full LiteLLM response as a dict.
    """
    response = completion(
        model=model,
        messages=messages,
        **kwargs,
    )
    return response  # type: ignore


@llm_circuit_breaker
def _call_primary(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Call primary LLM with circuit breaker protection."""
    return _call_llm(settings.llm_primary_model, messages, **kwargs)


def _call_fallback(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Call fallback LLM when primary circuit is open."""
    logger.warning("Primary LLM circuit open, using fallback: %s", settings.llm_fallback_model)
    return _call_llm(settings.llm_fallback_model, messages, **kwargs)


def call_llm(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> str:
    """Call LLM with automatic circuit breaker and fallback.

    Tries the primary model first. If the circuit breaker is open
    (5 consecutive failures), automatically routes to the fallback
    model. Returns the assistant's message content as a string.

    Args:
        messages: Chat messages in OpenAI format.
        **kwargs: Additional params (temperature, response_format, etc.).

    Returns:
        The assistant's response text.

    Raises:
        Exception: If both primary and fallback fail.
    """
    try:
        response = _call_primary(messages, **kwargs)
    except pybreaker.CircuitBreakerError:
        response = _call_fallback(messages, **kwargs)
    except Exception as exc:
        logger.error("Primary LLM failed: %s", exc)
        try:
            response = _call_fallback(messages, **kwargs)
        except Exception as fallback_exc:
            logger.error("Fallback LLM also failed: %s", fallback_exc)
            raise fallback_exc from exc

    return response.choices[0].message.content  # type: ignore


def call_llm_json(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Call LLM and parse the response as JSON.

    Adds response_format={"type": "json_object"} to force
    structured JSON output from the model.

    Args:
        messages: Chat messages in OpenAI format.
        **kwargs: Additional params (temperature, etc.).

    Returns:
        Parsed JSON dict from the assistant's response.

    Raises:
        json.JSONDecodeError: If the response isn't valid JSON.
        Exception: If both primary and fallback fail.
    """
    kwargs["response_format"] = {"type": "json_object"}
    raw = call_llm(messages, **kwargs)
    return json.loads(raw)
