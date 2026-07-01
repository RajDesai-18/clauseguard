"""Tests for bare-heading filtering in the clause splitter."""

from __future__ import annotations

from app.services.clause_splitter import _drop_bare_headings, _is_bare_heading

# Real bare headings observed from a DOCX MSA whose section bodies live in
# numbered subsections, leaving the top-level heading stranded as its own clause.
BARE_HEADINGS = [
    "16. Term and Termination",
    "9. Service Levels and Support",
    "4. Subscription Term; Auto-Renewal",
    "1. Definitions",
    "16.",
]

# Substantive clauses that must never be dropped.
REAL_CLAUSES = [
    "10. Suspension of Service\n\nIn addition to its suspension rights for "
    "non-payment, Provider may suspend Customer's access to the Services.",
    "16.3  Effect of Termination. Upon expiration or termination, Customer's "
    "right to access the Services ceases.",
    "6.Term and Termination. This NDA starts on the Effective Date and expires "
    "at the end of the Term of NDA.",
    "9.Disclaimer. Confidential Information is provided without warranties, "
    '"AS IS" and with all faults.',
    "IN WITNESS WHEREOF, the Parties have executed this Agreement.",
    "Additional Terms\nThe following additions to or modifications of the NDA.",
]


def test_detects_bare_headings():
    """Numbered headings with no clause body are identified as bare."""
    for text in BARE_HEADINGS:
        assert _is_bare_heading(text) is True, text


def test_keeps_real_clauses():
    """Clauses with substantive body text are never treated as headings."""
    for text in REAL_CLAUSES:
        assert _is_bare_heading(text) is False, text


def test_empty_text_is_not_heading():
    """Empty or whitespace-only text is not a bare heading."""
    assert _is_bare_heading("") is False
    assert _is_bare_heading("   ") is False


def test_unnumbered_short_phrase_is_kept():
    """A short phrase without a leading section number is never a heading."""
    assert _is_bare_heading("Confidential Information") is False


def test_drop_bare_headings_removes_only_headings_and_preserves_order():
    """Bare headings are dropped while real subsections keep their order."""
    clauses = [
        {"original_text": "4. Subscription Term; Auto-Renewal", "position": 1},
        {"original_text": "4.2  Automatic Renewal. The term renews on expiry.", "position": 2},
        {"original_text": "9. Service Levels and Support", "position": 3},
        {"original_text": "9.1  Availability. Provider uses reasonable efforts.", "position": 4},
    ]

    kept = _drop_bare_headings(clauses)

    assert len(kept) == 2
    assert kept[0]["original_text"].startswith("4.2")
    assert kept[1]["original_text"].startswith("9.1")


def test_drop_bare_headings_empty_list():
    """An empty clause list returns an empty list."""
    assert _drop_bare_headings([]) == []
