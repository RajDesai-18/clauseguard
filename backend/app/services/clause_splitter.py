"""Split raw contract text into individual clauses using LLM."""

from __future__ import annotations

import logging
import re
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
- Do NOT output a clause whose original_text is only a section heading or title
  (for example "16. Term and Termination"). Merge each section heading into the
  substantive clause body beneath it; every clause must contain actual
  contractual language, not just a heading.
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

# A bare heading is a leading section number followed by a short phrase with no
# sentence punctuation. A substantive clause contains at least one period.
_SECTION_NUM_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?(?:\s+|$)")
_MAX_HEADING_LEN = 60


def _is_bare_heading(original_text: str) -> bool:
    """Return True if the text is only a numbered section heading with no body.

    The LLM splitter occasionally emits a top-level section heading (for
    example "16. Term and Termination") as its own clause when the section's
    body lives entirely in numbered subsections. Such a clause carries no
    contractual content and pollutes both analysis and search.

    A bare heading is a leading section number followed by a short phrase (at
    most ``_MAX_HEADING_LEN`` characters) containing no sentence-ending period,
    since any substantive clause contains at least one.

    Args:
        original_text: The clause text emitted by the splitter.

    Returns:
        True if the text is only a section heading, False otherwise.
    """
    stripped = (original_text or "").strip()
    if not stripped:
        return False

    match = _SECTION_NUM_RE.match(stripped)
    if not match:
        return False

    body = stripped[match.end() :].strip()
    if not body:
        return True

    core = body[:-1].rstrip() if body.endswith(".") else body
    return len(core) <= _MAX_HEADING_LEN and "." not in core


def _drop_bare_headings(clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove clauses that are only numbered section headings.

    Args:
        clauses: The raw clause dicts from the splitter.

    Returns:
        The clauses with bare headings removed. Positions are left as-is; the
        caller renumbers.
    """
    kept: list[dict[str, Any]] = []
    for clause in clauses:
        text = clause.get("original_text", "")
        if _is_bare_heading(text):
            logger.info("Dropping bare-heading clause: %r", text[:80])
            continue
        kept.append(clause)
    return kept


def split_clauses(raw_text: str) -> dict[str, Any]:
    """Split contract text into classified clauses via LLM.

    Bare section headings emitted by the splitter (clauses whose text is only a
    numbered heading with no body) are dropped, and the remaining clauses are
    renumbered contiguously so ``position`` has no gaps.

    Args:
        raw_text: Full extracted text from the contract document.

    Returns:
        Dict with contract_type, summary, and the filtered list of clauses.

    Raises:
        ValueError: If raw_text is empty.
        Exception: If the LLM call fails or returns invalid JSON.
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

    raw_clauses = result.get("clauses", [])
    kept = _drop_bare_headings(raw_clauses)

    # Renumber positions contiguously after any drops so downstream ordering
    # has no gaps.
    for new_position, clause in enumerate(kept, 1):
        clause["position"] = new_position
    result["clauses"] = kept

    dropped = len(raw_clauses) - len(kept)
    logger.info(
        "Split contract into %d clauses (dropped %d bare heading(s)), type: %s",
        len(kept),
        dropped,
        result.get("contract_type", "unknown"),
    )

    return result
