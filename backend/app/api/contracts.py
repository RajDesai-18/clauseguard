"""Contract upload and retrieval endpoints."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid

from fastapi import APIRouter, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select

from app.api.deps import CurrentUser, DBSession
from app.core.storage import delete_file, upload_file
from app.models.clause import Clause
from app.models.contract import Contract
from app.schemas.clause import ClauseListResponse, ClauseResponse
from app.schemas.contract import (
    ContractDetail,
    ContractListResponse,
    ContractSummary,
    ContractUploadResponse,
)
from app.services.review_exporter import build_review_docx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["contracts"])

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
    current_user: CurrentUser,
) -> ContractUploadResponse:
    """Upload a PDF or DOCX contract for analysis.

    Validates file type and size, computes content hash for idempotency,
    uploads to MinIO, creates a DB record scoped to the current user,
    and dispatches the Celery pipeline.

    Duplicate detection is per-user: the same file uploaded by two
    different users produces two contracts.
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

    # Check for duplicate upload SCOPED to this user. The same file
    # uploaded by another user is a different contract; we don't share
    # analyses across users.
    existing = await db.execute(
        select(Contract).where(
            and_(
                Contract.file_hash == file_hash,
                Contract.user_id == current_user.id,
            )
        )
    )
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

    # Create contract record scoped to the current user
    contract = Contract(
        id=contract_id,
        user_id=current_user.id,
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

    run_pipeline(str(contract_id))

    logger.info(
        "Contract %s queued for processing (user=%s)",
        contract_id,
        current_user.id,
    )

    return ContractUploadResponse(
        id=contract.id,
        file_name=contract.file_name,
        status=contract.status,
    )


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    db: DBSession,
    current_user: CurrentUser,
    page: int = 1,
    size: int = 20,
) -> ContractListResponse:
    """List contracts for the current user, paginated."""
    offset = (page - 1) * size

    # Total count for this user
    count_result = await db.execute(
        select(func.count(Contract.id)).where(Contract.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Page of contracts
    result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
        .order_by(Contract.created_at.desc())
        .offset(offset)
        .limit(size)
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
    current_user: CurrentUser,
) -> ContractDetail:
    """Get a single contract owned by the current user.

    Returns 404 (not 403) if the contract exists but belongs to another
    user. We don't leak existence across the user boundary.
    """
    result = await db.execute(
        select(Contract).where(
            and_(
                Contract.id == contract_id,
                Contract.user_id == current_user.id,
            )
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )
    return ContractDetail.model_validate(contract)


@router.get("/{contract_id}/clauses", response_model=ClauseListResponse)
async def get_contract_clauses(
    contract_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ClauseListResponse:
    """Get clauses for a contract owned by the current user.

    Returns 404 if the contract doesn't exist or belongs to another user.
    """
    contract_result = await db.execute(
        select(Contract).where(
            and_(
                Contract.id == contract_id,
                Contract.user_id == current_user.id,
            )
        )
    )
    contract = contract_result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    # Fetch clauses ordered by position
    clauses_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id).order_by(Clause.position)
    )
    clauses = clauses_result.scalars().all()

    return ClauseListResponse(
        contract_id=str(contract.id),
        contract_type=contract.contract_type,
        overall_risk=contract.overall_risk,
        clause_count=len(clauses),
        clauses=[ClauseResponse.model_validate(c) for c in clauses],
    )


@router.get("/{contract_id}/export")
async def export_contract_review(
    contract_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Generate and download a Word document review of the contract.

    Returns a `.docx` file with the overall risk assessment, every
    risky clause's analysis (original text, plain-English explanation,
    market comparison, suggested revision), and a compact list of
    clauses reviewed without issue.

    Only available for contracts in terminal `complete` status. Returns
    409 for in-flight or failed contracts; the analysis isn't ready or
    is known to have failed.
    """
    contract_result = await db.execute(
        select(Contract).where(
            and_(
                Contract.id == contract_id,
                Contract.user_id == current_user.id,
            )
        )
    )
    contract = contract_result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    if contract.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"Contract analysis is not complete. Current status: {contract.status}."),
        )

    clauses_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id).order_by(Clause.position)
    )
    clauses = clauses_result.scalars().all()

    try:
        buffer = build_review_docx(contract, clauses)
    except Exception as exc:
        logger.exception("Failed to generate review DOCX for contract %s", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate review document.",
        ) from exc

    filename = _build_export_filename(contract.file_name)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Prevent intermediate caches from serving a stale review
            # if the user re-analyses the contract.
            "Cache-Control": "no-store",
        },
    )


def _build_export_filename(original: str) -> str:
    """Construct the download filename.

    Strips the source extension, sanitises the remainder to a portable
    character set, and prefixes with `clauseguard-review-`. Falls back
    to a safe default if sanitisation leaves nothing useful.
    """
    stem = re.sub(r"\.(pdf|docx|doc)$", "", original, flags=re.IGNORECASE)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not safe:
        safe = "contract"
    return f"clauseguard-review-{safe}.docx"


@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contract(
    contract_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    """Delete a contract permanently.

    Removes the MinIO file first, then the contract row. Clauses are
    cascade-deleted via the SQLAlchemy relationship. Returns 404 if the
    contract doesn't exist OR belongs to a different user (no cross-user
    existence leak, consistent with the rest of this router).

    Order matters: file before row. If the file delete fails, the row
    stays so the user can retry. Doing it the other way risks an
    orphaned MinIO object that we can't track because the only record
    pointing at it just got deleted.
    """
    result = await db.execute(
        select(Contract).where(
            and_(
                Contract.id == contract_id,
                Contract.user_id == current_user.id,
            )
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    # Snapshot the file key before the row goes away.
    file_url = contract.file_url

    try:
        delete_file(file_url)
    except Exception as exc:
        logger.exception(
            "Failed to delete MinIO object %s for contract %s",
            file_url,
            contract_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete contract file. Please try again.",
        ) from exc

    await db.delete(contract)
    await db.commit()

    logger.info(
        "Contract %s deleted (user=%s, file=%s)",
        contract_id,
        current_user.id,
        file_url,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
