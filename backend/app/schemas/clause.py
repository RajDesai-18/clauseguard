"""Pydantic schemas for clause API responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ClauseResponse(BaseModel):
    """Single clause in an analysis result."""

    id: uuid.UUID
    clause_type: str
    original_text: str
    risk_level: str
    explanation: str
    market_comparison: str | None = None
    suggested_redline: str | None = None
    position: int
    confidence: float

    model_config = {"from_attributes": True}


class ClauseListResponse(BaseModel):
    """Response for listing all clauses of a contract."""

    contract_id: str
    contract_type: str | None = None
    overall_risk: str | None = None
    clause_count: int
    clauses: list[ClauseResponse]
