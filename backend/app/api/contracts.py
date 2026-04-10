"""Contract upload and retrieval endpoints."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.storage import upload_file
from app.models.contract import Contract
from app.schemas.contract import (
    ContractDetail,
    ContractListResponse,
    ContractSummary,
    ContractUploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["contracts"])

DBSession = Annotated[AsyncSession, Depends(get_db)]

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/upload",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_contract(
    file: UploadFile,
    db: DBSession,
) -> ContractUploadResponse:
    """Upload a PDF or DOCX contract for analysis.

    Validates file type and size, computes content hash for idempotency,
    uploads to MinIO, creates a DB record, and dispatches the Celery pipeline.
    """
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and DOCX are accepted.",
        )

    # Read file content
    content = await file.read()

    # Validate size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Compute content hash for idempotency
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate upload
    existing = await db.execute(select(Contract).where(Contract.file_hash == file_hash))
    duplicate = existing.scalar_one_or_none()
    if duplicate is not None:
        return ContractUploadResponse(
            id=duplicate.id,
            file_name=duplicate.file_name,
            status=duplicate.status,
            message="Duplicate file detected. Returning existing analysis.",
        )

    # Upload to MinIO
    contract_id = uuid.uuid4()
    extension = file.filename.rsplit(".", 1)[-1] if file.filename else "bin"
    object_key = f"{contract_id}.{extension}"

    try:
        upload_file(
            file_bytes=content,
            object_name=object_key,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        logger.exception("Failed to upload file to MinIO")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store file. Please try again.",
        ) from exc

    # Create contract record
    contract = Contract(
        id=contract_id,
        file_name=file.filename or "unknown",
        file_url=object_key,
        file_hash=file_hash,
        status="queued",
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    # Dispatch Celery pipeline
    from app.tasks.pipeline import run_pipeline

    run_pipeline.delay(str(contract_id))  # type: ignore

    logger.info("Contract %s queued for processing", contract_id)

    return ContractUploadResponse(
        id=contract.id,
        file_name=contract.file_name,
        status=contract.status,
    )


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    db: DBSession,
    page: int = 1,
    size: int = 20,
) -> ContractListResponse:
    """List all contracts with pagination."""
    offset = (page - 1) * size

    # Get total count
    count_result = await db.execute(select(func.count(Contract.id)))
    total = count_result.scalar_one()

    # Get page of contracts
    result = await db.execute(
        select(Contract).order_by(Contract.created_at.desc()).offset(offset).limit(size)
    )
    contracts = result.scalars().all()

    return ContractListResponse(
        items=[ContractSummary.model_validate(c) for c in contracts],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: uuid.UUID,
    db: DBSession,
) -> ContractDetail:
    """Get a single contract with full details."""
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )
    return ContractDetail.model_validate(contract)
