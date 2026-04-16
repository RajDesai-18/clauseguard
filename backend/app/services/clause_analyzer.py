"""Clause risk analysis and explanation via LLM."""

from __future__ import annotations

import logging
from typing import Any

from app.services.llm_client import call_llm_json
from app.services.template_matcher import find_nearest_template

logger = logging.getLogger(__name__)

ANALYZE_CLAUSE_PROMPT = """You are an expert contract attorney reviewing a clause for risk.
Analyze the following clause from a {contract_type} contract.

Return a JSON object with this exact structure:
{{
    "risk_level": "green" | "yellow" | "red",
    "confidence": 0.0 to 1.0,
    "explanation": "Plain-English explanation of the risk (2-4 sentences)",
    "market_comparison": "How this compares to market-standard language (1-2 sentences)"
}}

Risk level definitions:
- green: Standard, fair, market-typical language. No action needed.
- yellow: Somewhat unusual or one-sided. Worth reviewing but not dangerous.
- red: Highly unfavorable, missing key protections, or potentially harmful. Needs revision.

Rules:
- Write explanations a non-lawyer can understand. No legal jargon without explanation.
- Be specific about WHAT makes it risky, not just that it IS risky.
- market_comparison should reference what a typical {contract_type} clause looks like.
- confidence reflects how certain you are in the risk assessment (0.8+ for clear cases)."""

TEMPLATE_CONTEXT = """

MARKET-STANDARD REFERENCE (similarity: {similarity:.0%}):
The following is a market-standard {clause_type} clause for {contract_type} contracts.
Use this as a grounded reference point for your market_comparison analysis.
Do NOT copy this text into your response. Instead, compare the clause under review
against this standard to identify specific deviations.

---
{standard_text}
---"""


def analyze_clause(
    clause_text: str,
    clause_type: str,
    contract_type: str,
) -> dict[str, Any]:
    """Analyze a single clause for risk level and explanation.

    Searches for the nearest market-standard template via pgvector
    and includes it as grounded context in the LLM prompt when a
    relevant match is found.

    Args:
        clause_text: The exact text of the clause.
        clause_type: Type of clause (e.g. indemnification, termination).
        contract_type: Type of contract (e.g. nda, msa, lease).

    Returns:
        Dict with risk_level, confidence, explanation, and market_comparison.

    Raises:
        Exception: If LLM call fails or returns invalid JSON.
    """
    system_prompt = ANALYZE_CLAUSE_PROMPT.format(contract_type=contract_type)

    # Search for nearest market-standard template
    template = find_nearest_template(clause_text, contract_type)
    if template is not None and template["similarity"] >= 0.5:
        system_prompt += TEMPLATE_CONTEXT.format(
            similarity=template["similarity"],
            clause_type=template["clause_type"],
            contract_type=contract_type,
            standard_text=template["standard_text"],
        )
        logger.info(
            "Enriched analysis prompt with template: %s (similarity: %.4f)",
            template["clause_type"],
            template["similarity"],
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (f"Clause type: {clause_type}\n\nClause text:\n{clause_text}"),
        },
    ]

    result = call_llm_json(messages, temperature=0.0)

    # Validate and normalize the response
    valid_levels = {"green", "yellow", "red"}
    if result.get("risk_level") not in valid_levels:
        logger.warning(
            "Invalid risk_level '%s' for clause type '%s', defaulting to yellow",
            result.get("risk_level"),
            clause_type,
        )
        result["risk_level"] = "yellow"

    confidence = result.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
        result["confidence"] = 0.5

    logger.info(
        "Analyzed clause '%s': %s (confidence: %.2f)",
        clause_type,
        result["risk_level"],
        result["confidence"],
    )

    return result
