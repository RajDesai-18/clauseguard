"""Contract upload and retrieval endpoints."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, delete, func, select

from app.api.deps import CurrentUser, DBSession
from app.core.storage import delete_file, upload_file
from app.models.clause import Clause
from app.core.config import settings
from app.services.progress import CHANNEL_PREFIX
from app.models.contract import Contract
from app.schemas.clause import ClauseListResponse, ClauseResponse
from app.schemas.contract import (
    ContractDetail,
    ContractListResponse,
    ContractSummary,
    ContractUploadResponse,
)
from app.services.result_cache import (
    get_cached_clauses,
    invalidate_contract_cache,
    set_cached_clauses,
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

    Idempotency is per-user and keyed on file content (SHA-256):

    - An in-flight or completed duplicate is returned as-is, so the
      caller attaches to the existing job or result instead of spawning
      a second pipeline for identical bytes.
    - A previously *failed* duplicate is purged and re-processed, so the
      same file isn't permanently stuck on a dead record. Reuploading is
      the natural retry gesture; we honour it.

    The same file uploaded by two different users produces two
    contracts; analyses are never shared across the user boundary.
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

    # Check for a duplicate upload SCOPED to this user. The same file
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
        if duplicate.status != "failed":
            # In-flight or complete: attach to the existing contract
            # rather than reprocessing identical bytes.
            logger.info(
                "Duplicate upload for hash %s returned existing contract %s (status=%s, user=%s)",
                file_hash[:12],
                duplicate.id,
                duplicate.status,
                current_user.id,
            )
            return ContractUploadResponse(
                id=duplicate.id,
                file_name=duplicate.file_name,
                status=duplicate.status,
                message="Duplicate file detected. Returning existing analysis.",
            )

        # A prior attempt failed. Purge the dead record and its file so
        # this upload becomes a clean retry instead of returning a
        # contract the user can never move forward.
        logger.info(
            "Re-uploading previously failed contract %s for hash %s; "
            "purging dead record (user=%s)",
            duplicate.id,
            file_hash[:12],
            current_user.id,
        )
        try:
            delete_file(duplicate.file_url)
        except Exception:
            # Best-effort cleanup. A leftover object is undesirable but
            # not fatal; don't block the retry on storage cleanup.
            logger.warning(
                "Failed to delete MinIO object %s for failed contract %s; continuing with retry",
                duplicate.file_url,
                duplicate.id,
            )
        await db.delete(duplicate)
        await db.commit()

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

@router.get("/{contract_id}/stream")
async def stream_contract_progress(
    contract_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Stream live pipeline progress for a contract via Server-Sent Events.

    Subscribes to the Redis channel the pipeline publishes progress to and
    forwards each event to the browser as an SSE frame. Authenticated and
    ownership-checked like every other endpoint in this router; returns 404
    if the contract doesn't exist or belongs to another user.

    Implementation notes:

    - A FRESH async Redis client is created inside the generator and closed in
      `finally`. The shared `get_redis()` singleton binds its connection pool
      to the first event loop it sees, which misbehaves for a long-lived
      subscription under ASGI, so it must not be used here.
    - On connect we check the contract's current status. If it is already
      terminal (`complete`/`failed`), we emit that once and close, handling the
      race where the pipeline finishes before the browser opens the stream.
    - An idle heartbeat comment keeps the connection alive through proxy idle
      timeouts (Caddy in production).
    - The generator's `finally` unsubscribes and closes the client so a browser
      disconnect doesn't leak a Redis connection.
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

    initial_status = contract.status
    channel = f"{CHANNEL_PREFIX}{contract_id}"

    async def event_generator() -> AsyncGenerator[str, None]:
        import redis.asyncio as aioredis

        # Fresh client bound to THIS request's event loop (see docstring).
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(channel)

            # Tell the client the stream is open.
            yield "event: connected\ndata: {}\n\n"

            # Already-complete race: if the contract is already terminal, emit
            # a final event and close rather than waiting for events that will
            # never come.
            if initial_status in ("complete", "failed"):
                payload = json.dumps(
                    {
                        "contract_id": str(contract_id),
                        "status": initial_status,
                        "detail": "Analysis already complete.",
                        "current_step": 5,
                        "total_steps": 5,
                    }
                )
                yield f"data: {payload}\n\n"
                return

            # Forward events as they are published, with idle heartbeats.
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=15.0
                )
                if message is None:
                    # Idle period: heartbeat comment keeps the connection open.
                    yield ": keepalive\n\n"
                    continue

                data = message["data"]
                yield f"data: {data}\n\n"

                # Stop once the pipeline reaches a terminal state.
                try:
                    parsed = json.loads(data)
                    if parsed.get("status") in ("complete", "failed", "error"):
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            finally:
                await client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable proxy buffering (nginx-style hint; harmless elsewhere).
            "X-Accel-Buffering": "no",
        },
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
) -> Response:
    """Get clauses for a contract owned by the current user.

    Returns 404 if the contract doesn't exist or belongs to another user.

    For contracts in terminal ``complete`` status the assembled response
    is served through a read-through Redis cache. The analysis is
    immutable once complete, so a cached payload cannot go stale within
    its TTL. Ownership is always verified against PostgreSQL first, so
    the cache never short-circuits the access-control check. In-flight
    contracts bypass the cache, since their clause set is still changing.

    Returns a raw ``Response`` rather than the model so a cache hit skips
    re-serialisation; ``response_model`` is retained for the OpenAPI schema.
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

    cache_id = str(contract_id)
    is_cacheable = contract.status == "complete"

    # Read-through: serve a cached payload if one exists.
    if is_cacheable:
        cached = await get_cached_clauses(cache_id)
        if cached is not None:
            return Response(content=cached, media_type="application/json")

    # Cache miss, or a non-terminal status: assemble from the database.
    clauses_result = await db.execute(
        select(Clause).where(Clause.contract_id == contract_id).order_by(Clause.position)
    )
    clauses = clauses_result.scalars().all()

    response_model = ClauseListResponse(
        contract_id=str(contract.id),
        contract_type=contract.contract_type,
        overall_risk=contract.overall_risk,
        clause_count=len(clauses),
        clauses=[ClauseResponse.model_validate(c) for c in clauses],
    )
    payload = response_model.model_dump_json()

    # Populate the cache only for immutable, completed analyses.
    if is_cacheable:
        await set_cached_clauses(cache_id, payload)

    return Response(content=payload, media_type="application/json")


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

    # Free the cached analysis promptly. Even without this the ownership
    # check above would 404 a deleted contract before reaching the cache,
    # but purging now reclaims Redis memory instead of waiting on the TTL.
    await invalidate_contract_cache(str(contract_id))

    logger.info(
        "Contract %s deleted (user=%s, file=%s)",
        contract_id,
        current_user.id,
        file_url,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{contract_id}/reanalyze",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reanalyze_contract(
    contract_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ContractUploadResponse:
    """Re-run the analysis pipeline for a contract the current user owns.

    Resets the contract to ``queued``, clears its existing clauses and any
    prior analysis (risk, summary, contract type, degraded reason), invalidates
    the cached result, and re-dispatches the same Celery saga used at upload.
    The stored file is re-parsed and re-analysed from scratch, so a re-analysis
    also picks up any parser or splitter improvements made since the original
    run.

    Only contracts in a terminal state (``complete`` or ``failed``) may be
    re-analysed. Re-analysing an in-flight contract would race the running
    pipeline and could double-write clauses, so those return 409. Returns 404
    if the contract doesn't exist or belongs to another user (no cross-user
    existence leak, consistent with the rest of this router).

    The frontend re-opens the SSE progress stream on the same contract id to
    watch the re-run live, exactly as it does for a fresh upload.
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

    # Only terminal contracts may be re-analysed. An in-flight pipeline would
    # race a second dispatch and could double-write clauses for the contract.
    if contract.status not in ("complete", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Contract is still processing (status: {contract.status}). "
                "Wait for it to finish before re-analysing."
            ),
        )

    # Clear the previous analysis. Clauses are regenerated by the pipeline; the
    # analysis-derived fields are reset so the contract reads as a clean queued
    # job while it reprocesses. File metadata (name, url, hash) is left intact.
    await db.execute(delete(Clause).where(Clause.contract_id == contract_id))
    contract.status = "queued"
    contract.degraded_reason = None
    contract.overall_risk = None
    contract.summary = None
    contract.contract_type = None
    contract.clause_count = 0
    contract.analyzed_at = None
    await db.commit()

    # Drop the now-stale cached analysis payload.
    await invalidate_contract_cache(str(contract_id))

    # Re-dispatch the same saga used at upload.
    from app.tasks.pipeline import run_pipeline

    run_pipeline(str(contract_id))

    logger.info(
        "Contract %s re-analysis dispatched (user=%s)",
        contract_id,
        current_user.id,
    )

    return ContractUploadResponse(
        id=contract.id,
        file_name=contract.file_name,
        status=contract.status,
        message="Re-analysis started.",
    )
