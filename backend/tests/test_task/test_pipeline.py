"""Tests for saga pure-logic helpers (no DB, no Celery)."""

from __future__ import annotations

from app.celery_app import ping
from app.tasks.score import _compute_overall_risk

# ---------------------------------------------------------------
# Ping task (smoke test for Celery app wiring)
# ---------------------------------------------------------------


def test_ping_task():
    """Ping task should return pong."""
    assert ping() == "pong"


# ---------------------------------------------------------------
# Overall risk computation
# ---------------------------------------------------------------
# In the saga, _compute_overall_risk lives in score.py and operates
# on a list of risk_level strings (read from the DB) rather than
# dicts. Same logic, simpler signature.


def test_overall_risk_all_green_is_low():
    """All green clauses should produce low overall risk."""
    assert _compute_overall_risk(["green"] * 5) == "low"


def test_overall_risk_any_red_is_high():
    """A single red clause should make overall risk high."""
    assert _compute_overall_risk(["green", "green", "red"]) == "high"


def test_overall_risk_three_or_more_yellows_is_high():
    """3+ yellow clauses with no red should produce high risk."""
    assert _compute_overall_risk(["yellow", "yellow", "yellow", "green"]) == "high"


def test_overall_risk_one_or_two_yellows_is_medium():
    """1-2 yellow clauses with no red should produce medium risk."""
    assert _compute_overall_risk(["yellow", "green"]) == "medium"
    assert _compute_overall_risk(["yellow", "yellow", "green"]) == "medium"


def test_overall_risk_empty_clauses_is_low():
    """No clauses should produce low risk (vacuously)."""
    assert _compute_overall_risk([]) == "low"


def test_overall_risk_red_dominates_yellows():
    """A red clause should always produce high risk, regardless of yellow count."""
    assert _compute_overall_risk(["yellow"] * 5 + ["red"]) == "high"


def test_overall_risk_only_reds_is_high():
    """Multiple red clauses should produce high risk."""
    assert _compute_overall_risk(["red", "red"]) == "high"


def test_overall_risk_mixed_at_yellow_threshold():
    """Exactly 3 yellows with one green is the threshold for high risk."""
    assert _compute_overall_risk(["yellow", "yellow", "yellow"]) == "high"
    assert _compute_overall_risk(["yellow", "yellow"]) == "medium"
