"""Generate suggested redline revisions for risky clauses."""

from __future__ import annotations

import logging

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

REDLINE_PROMPT = """You are an expert contract attorney drafting a revision for a risky clause.
The clause below is from a {contract_type} contract and has been flagged as {risk_level} risk.

Risk explanation: {explanation}

Rewrite the clause to be fairer and more balanced while preserving the original intent.

Rules:
- Keep the same general structure and legal meaning.
- Remove or soften overly one-sided language.
- Add missing protections that are market-standard for {contract_type} agreements.
- Write in clear, professional legal language.
- Do NOT add commentary or explanation. Return ONLY the revised clause text.
- If the clause is short, the revision should be similarly concise."""


def generate_redline(
    clause_text: str,
    clause_type: str,
    contract_type: str,
    risk_level: str,
    explanation: str,
) -> str | None:
    """Generate a suggested redline revision for a risky clause.

    Only generates redlines for yellow and red risk clauses.
    Green clauses return None (no revision needed).

    Args:
        clause_text: The exact text of the clause.
        clause_type: Type of clause (e.g. indemnification, termination).
        contract_type: Type of contract (e.g. nda, msa, lease).
        risk_level: The assessed risk level (green, yellow, red).
        explanation: Plain-English explanation of why it's risky.

    Returns:
        Suggested revised clause text, or None for green clauses.
    """
    if risk_level == "green":
        logger.debug("Skipping redline for green clause: %s", clause_type)
        return None

    system_prompt = REDLINE_PROMPT.format(
        contract_type=contract_type,
        risk_level=risk_level,
        explanation=explanation,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (f"Clause type: {clause_type}\n\nOriginal clause:\n{clause_text}"),
        },
    ]

    redline = call_llm(messages, temperature=0.3)

    logger.info(
        "Generated redline for %s clause (%s risk): %d chars",
        clause_type,
        risk_level,
        len(redline),
    )

    return redline.strip()
