"""Account-level data operations.

Currently exposes a single endpoint that purges everything ClauseGuard
owns for the current user: their contracts, the clauses derived from
them, and the contracts' stored files in MinIO.

This endpoint deliberately does NOT touch Better Auth's tables (`user`,
`session`, `account`). Deleting the auth user is orchestrated by the
Next.js layer, which calls this endpoint first, while the session is
still valid, and only then removes the auth user through Better Auth.
If the auth user were deleted first, this endpoint could no longer
authenticate the caller (FastAPI resolves the user by reading the
`session` table), stranding the user's files in MinIO with no record
pointing at them.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser, DBSession
from app.core.storage import delete_file
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.result_cache import invalidate_contract_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])


class PurgeSummary(BaseModel):
    """Counts of what an account-data purge removed."""

    deleted_contracts: int
    deleted_clauses: int


@router.delete("/data", response_model=PurgeSummary)
async def purge_account_data(
    db: DBSession,
    current_user: CurrentUser,
) -> PurgeSummary:
    """Permanently delete all of the current user's contracts, clauses, and files.

    Scoped strictly to the authenticated user: every query filters on
    ``current_user.id``, so a caller can only ever purge their own data.

    Ordering mirrors the single-contract delete: MinIO objects are removed
    before the database rows. If any file delete fails, the endpoint aborts
    with 502 *before* touching the database, leaving every row intact so the
    whole purge can be retried. ``delete_file`` is idempotent (deleting a
    missing object succeeds), so a retry safely no-ops the files it already
    removed.

    Returns the number of contracts and clauses deleted. A user with no
    contracts gets a zeroed summary and a 200, so the Next.js orchestrator
    can treat "nothing to purge" and "purged successfully" identically before
    proceeding to delete the auth user.

    Args:
        db: Async database session.
        current_user: The authenticated user whose data is purged.

    Returns:
        A summary with the counts of deleted contracts and clauses.

    Raises:
        HTTPException: 502 if one or more MinIO objects could not be deleted.
    """
    # Load the user's contracts. We need their file keys (to delete the
    # MinIO objects) and their ids (to invalidate cached analyses).
    result = await db.execute(select(Contract).where(Contract.user_id == current_user.id))
    contracts = result.scalars().all()

    if not contracts:
        return PurgeSummary(deleted_contracts=0, deleted_clauses=0)

    contract_ids = [c.id for c in contracts]

    # Count clauses up front for the summary; they are removed below.
    clause_count_result = await db.execute(
        select(func.count(Clause.id)).where(Clause.contract_id.in_(contract_ids))
    )
    deleted_clauses = clause_count_result.scalar_one()

    # Files before rows. Collect any failures and abort before the DB writes
    # so the operation stays retryable (see docstring).
    failed_files: list[str] = []
    for contract in contracts:
        try:
            delete_file(contract.file_url)
        except Exception:
            logger.exception(
                "Failed to delete MinIO object %s during account purge (user=%s)",
                contract.file_url,
                current_user.id,
            )
            failed_files.append(contract.file_url)

    if failed_files:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete some contract files. Please try again.",
        )

    # Rows: clauses first (explicit, mirroring the reanalyze path), then
    # contracts. The clause delete is also covered by the ON DELETE CASCADE on
    # clauses.contract_id, but doing it explicitly keeps the intent clear and
    # independent of that constraint.
    await db.execute(delete(Clause).where(Clause.contract_id.in_(contract_ids)))
    await db.execute(delete(Contract).where(Contract.user_id == current_user.id))
    await db.commit()

    # Drop each contract's cached analysis. The ownership check would 404 a
    # deleted contract anyway, but purging now reclaims Redis memory instead of
    # waiting on the TTL.
    for contract_id in contract_ids:
        await invalidate_contract_cache(str(contract_id))

    logger.info(
        "Purged account data for user=%s: %d contracts, %d clauses",
        current_user.id,
        len(contracts),
        deleted_clauses,
    )

    return PurgeSummary(
        deleted_contracts=len(contracts),
        deleted_clauses=deleted_clauses,
    )
