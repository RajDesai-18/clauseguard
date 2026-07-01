"""Cross-contract semantic clause search endpoint."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.schemas.search import SearchContractGroup, SearchHit, SearchResponse
from app.services.clause_search import search_clauses

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    current_user: CurrentUser,
    q: str = Query(..., min_length=2, max_length=500, description="Search query."),
    limit: int = Query(30, ge=1, le=100, description="Max clause hits to return."),
) -> SearchResponse:
    """Semantic search across the current user's analysed clauses.

    Embeds the query and runs a pgvector similarity search over every clause
    belonging to the user, then groups the hits by source contract (groups and
    hits both ordered most-similar first).

    The embedding call and DB round-trip are blocking, so they run in a worker
    thread to keep the event loop free. A failure of either (e.g. the embedding
    provider being down) surfaces as 503, distinct from an empty-but-successful
    search.
    """
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query must not be empty.",
        )

    try:
        hits = await asyncio.to_thread(search_clauses, query, str(current_user.id), limit)
    except Exception:
        logger.exception("Clause search failed for user=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search is temporarily unavailable. Please try again.",
        ) from None

    # Group flat hits by contract, preserving global similarity order. Because
    # `hits` is sorted most-similar first, a contract's first-seen hit is also
    # its best, so insertion order yields correctly ranked groups.
    groups: dict[str, SearchContractGroup] = {}
    for hit in hits:
        cid = hit["contract_id"]
        group = groups.get(cid)
        if group is None:
            group = SearchContractGroup(
                contract_id=cid,
                file_name=hit["file_name"],
                contract_type=hit["contract_type"],
                overall_risk=hit["overall_risk"],
                top_similarity=hit["similarity"],
                hits=[],
            )
            groups[cid] = group
        group.hits.append(
            SearchHit(
                clause_id=hit["clause_id"],
                clause_type=hit["clause_type"],
                risk_level=hit["risk_level"],
                original_text=hit["original_text"],
                explanation=hit["explanation"],
                position=hit["position"],
                similarity=hit["similarity"],
            )
        )

    return SearchResponse(
        query=query,
        total_hits=len(hits),
        groups=list(groups.values()),
    )
