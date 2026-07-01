"""LLM client with circuit breaker and provider fallback."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import pybreaker
from litellm import completion

from app.core.config import settings
from app.services.text_cleaning import fix_mojibake

logger = logging.getLogger(__name__)


class LLMUnavailableError(Exception):
    """Raised when both primary and fallback LLM providers are unreachable.

    Distinct from errors like malformed JSON or a bad prompt: this means
    the LLM service itself could not be reached (primary circuit open and
    fallback also failing), which is the precise condition that should
    trigger graceful degradation rather than a hard pipeline failure.
    """


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


def _complete(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> str:
    """Run a completion with circuit-breaker fallback, returning raw content.

    Tries the primary model; on failure or an open circuit, routes to the
    fallback. Returns the assistant's message content exactly as produced by
    the model, without post-processing. Callers apply mojibake repair in the
    way appropriate to their output shape (raw text vs. parsed JSON).

    Raises:
        LLMUnavailableError: If both primary and fallback are unreachable.
    """
    try:
        response = _call_primary(messages, **kwargs)
    except pybreaker.CircuitBreakerError:
        # Primary breaker is open. Try the fallback; if that also fails,
        # the LLM is genuinely unavailable.
        try:
            response = _call_fallback(messages, **kwargs)
        except Exception as fallback_exc:
            logger.error("Primary circuit open and fallback failed: %s", fallback_exc)
            raise LLMUnavailableError(
                "Both primary and fallback LLM providers are unavailable."
            ) from fallback_exc
    except Exception as exc:
        logger.error("Primary LLM failed: %s", exc)
        try:
            response = _call_fallback(messages, **kwargs)
        except Exception as fallback_exc:
            logger.error("Fallback LLM also failed: %s", fallback_exc)
            raise LLMUnavailableError(
                "Both primary and fallback LLM providers are unavailable."
            ) from fallback_exc

    return response.choices[0].message.content  # type: ignore


def _fix_mojibake_deep(value: Any) -> Any:
    """Recursively repair mojibake in every string within a parsed structure.

    Applied to parsed JSON (dicts, lists, scalars) *after* ``json.loads`` so
    repairing text can never corrupt JSON syntax. ftfy straightens curly
    quotes, and straightening a curly quote inside a raw JSON string would
    turn it into an unescaped ``"`` and break parsing, so cleaning must happen
    post-parse. Non-string scalars pass through untouched.
    """
    if isinstance(value, str):
        return fix_mojibake(value)
    if isinstance(value, dict):
        return {key: _fix_mojibake_deep(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_fix_mojibake_deep(item) for item in value]
    return value


def call_llm(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> str:
    """Call the LLM and return the assistant's text, mojibake-repaired.

    Tries the primary model first, automatically routing to the fallback if
    the circuit breaker is open. The returned text is passed through
    ``fix_mojibake`` so encoding damage the model may emit (for example a
    curly apostrophe surfacing as ``â€™``) never reaches the database.

    Args:
        messages: Chat messages in OpenAI format.
        **kwargs: Additional params (temperature, response_format, etc.).

    Returns:
        The assistant's response text, cleaned.

    Raises:
        LLMUnavailableError: If both primary and fallback are unreachable.
    """
    content = _complete(messages, **kwargs)
    return fix_mojibake(content) if content else content


def call_llm_json(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Call the LLM and parse the response as JSON, mojibake-repaired.

    Adds ``response_format={"type": "json_object"}`` to force structured
    output. The raw response is parsed first, then every string value is
    repaired via ``fix_mojibake``. Cleaning happens *after* parsing so it can
    never corrupt the JSON syntax itself.

    Args:
        messages: Chat messages in OpenAI format.
        **kwargs: Additional params (temperature, etc.).

    Returns:
        Parsed JSON dict with all string values mojibake-repaired.

    Raises:
        json.JSONDecodeError: If the response isn't valid JSON.
        LLMUnavailableError: If both primary and fallback are unreachable.
    """
    kwargs["response_format"] = {"type": "json_object"}
    raw = _complete(messages, **kwargs)
    parsed = json.loads(raw)
    return _fix_mojibake_deep(parsed)
