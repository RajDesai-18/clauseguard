"""Pydantic schemas for contract API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ContractUploadResponse(BaseModel):
    """Response after uploading a contract."""

    id: uuid.UUID
    file_name: str
    status: str
    message: str = "Contract queued for processing"


class ContractSummary(BaseModel):
    """Contract list item."""

    id: uuid.UUID
    file_name: str
    contract_type: str | None = None
    status: str
    overall_risk: str | None = None
    clause_count: int = 0
    created_at: datetime
    analyzed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContractDetail(ContractSummary):
    """Full contract detail."""

    summary: str | None = None
    file_url: str


class ContractListResponse(BaseModel):
    """Paginated contract list."""

    items: list[ContractSummary]
    total: int
    page: int
    size: int
