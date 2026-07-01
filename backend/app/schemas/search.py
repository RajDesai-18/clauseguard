"""Pydantic schemas for the clause search API."""

from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    """A single clause matched by a search query."""

    clause_id: str
    clause_type: str
    risk_level: str
    original_text: str
    explanation: str
    position: int
    similarity: float


class SearchContractGroup(BaseModel):
    """Search hits grouped under their source contract."""

    contract_id: str
    file_name: str
    contract_type: str | None = None
    overall_risk: str | None = None
    top_similarity: float
    hits: list[SearchHit]


class SearchResponse(BaseModel):
    """Response for a cross-contract clause search."""

    query: str
    total_hits: int
    groups: list[SearchContractGroup]
