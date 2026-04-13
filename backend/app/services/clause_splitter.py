"""Split raw contract text into individual clauses using LLM."""

from __future__ import annotations

import logging
from typing import Any

from app.services.llm_client import call_llm_json

logger = logging.getLogger(__name__)

CLAUSE_SPLIT_PROMPT = """You are a legal document analyst. Given the full text of a contract,
split it into individual clauses and classify each one.

Return a JSON object with this exact structure:
{
    "contract_type": "nda" | "msa" | "sow" | "freelance" | "lease" | "other",
    "summary": "A 2-3 sentence plain-English summary of what this contract does",
    "clauses": [
        {
            "clause_type": "string (e.g. indemnification, termination, confidentiality, etc.)",
            "original_text": "The exact text of this clause from the document",
            "position": 1
        }
    ]
}

Rules:
- Extract EVERY substantive clause. Do not skip any.
- Use lowercase_snake_case for clause_type values.
- Keep original_text as the exact wording from the document. Do not paraphrase.
- Position starts at 1 and increments sequentially.
- contract_type must be one of: nda, msa, sow, freelance, lease, other.
- The summary should be understandable by someone with no legal background.

Valid clause_type values include (but are not limited to):
- indemnification, termination, limitation_of_liability, governing_law
- dispute_resolution, assignment, force_majeure, severability
- confidentiality, non_disclosure, non_compete, non_solicitation
- definition_of_confidential_info, exclusions, return_of_materials, duration
- payment_terms, intellectual_property, scope_of_work, warranty
- acceptance_criteria, work_for_hire, late_payment, independent_contractor
- rent_payment, security_deposit, lease_duration, early_termination
- maintenance_and_repairs, subletting, property_use, rent_increase
- entry_and_access, insurance_requirements, default_and_remedies, utilities
- entire_agreement, notices, amendments, representations_and_warranties"""


def split_clauses(raw_text: str) -> dict[str, Any]:
    """Split contract text into classified clauses via LLM.

    Args:
        raw_text: Full extracted text from the contract document.

    Returns:
        Dict with contract_type, summary, and list of clauses.

    Raises:
        Exception: If LLM call fails or returns invalid JSON.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot split clauses from empty text")

    # Truncate extremely long contracts to stay within context limits
    max_chars = 100_000
    text = raw_text[:max_chars]
    if len(raw_text) > max_chars:
        logger.warning(
            "Contract text truncated from %d to %d characters",
            len(raw_text),
            max_chars,
        )

    messages = [
        {"role": "system", "content": CLAUSE_SPLIT_PROMPT},
        {"role": "user", "content": f"Here is the contract text:\n\n{text}"},
    ]

    result = call_llm_json(messages, temperature=0.0)

    clause_count = len(result.get("clauses", []))
    logger.info(
        "Split contract into %d clauses, type: %s",
        clause_count,
        result.get("contract_type", "unknown"),
    )

    return result
