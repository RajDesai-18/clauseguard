"""Backfill: repair mojibake in already-stored contract and clause text.

Earlier uploads (PDF path) stored text that was UTF-8 mis-decoded as
Windows-1252, so curly quotes surface as mojibake. The parser now repairs this
at ingest via ``app.services.text_cleaning.fix_mojibake``; this script applies
the same repair to rows already in the database.

Pure text repair: no LLM calls, no re-analysis, no cost. Idempotent, since clean
text is returned unchanged, so a second run changes nothing. The analysis result
cache is invalidated for affected contracts so the clauses endpoint stops
serving the stale (pre-repair) payload.

Usage:
    docker compose exec api python -m scripts.fix_mojibake --dry-run
    docker compose exec api python -m scripts.fix_mojibake
"""

from __future__ import annotations

import argparse
import logging
import sys

import redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.clause import Clause
from app.models.contract import Contract
from app.services.text_cleaning import fix_mojibake

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fix_mojibake")

CONTRACT_FIELDS = ["raw_text", "summary"]
CLAUSE_FIELDS = ["original_text", "explanation", "market_comparison", "suggested_redline"]
CACHE_KEY_PREFIX = "contract:clauses:"


def _sync_engine():
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return create_engine(sync_url)


def _repair_row(obj: object, fields: list[str]) -> int:
    """Repair the given text fields on a row in place; return count changed."""
    changed = 0
    for field in fields:
        value = getattr(obj, field)
        if not value:
            continue
        fixed = fix_mojibake(value)
        if fixed != value:
            setattr(obj, field, fixed)
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair mojibake in stored text.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to the database.",
    )
    args = parser.parse_args()

    engine = _sync_engine()
    contracts_changed = 0
    clauses_changed = 0
    affected: set[str] = set()

    with Session(engine) as session:
        contracts = session.execute(select(Contract)).scalars().all()
        for contract in contracts:
            if _repair_row(contract, CONTRACT_FIELDS):
                contracts_changed += 1
                affected.add(str(contract.id))

        clauses = session.execute(select(Clause)).scalars().all()
        for clause in clauses:
            if _repair_row(clause, CLAUSE_FIELDS):
                clauses_changed += 1
                affected.add(str(clause.contract_id))

        logger.info("Contracts with repairs: %d / %d", contracts_changed, len(contracts))
        logger.info("Clauses with repairs:   %d / %d", clauses_changed, len(clauses))
        logger.info("Affected contracts:     %d", len(affected))

        if args.dry_run:
            session.rollback()
            logger.info("Dry run: no changes written.")
            return 0

        session.commit()
        logger.info("Committed repairs to the database.")

    if affected:
        try:
            client = redis.from_url(settings.redis_url)
            deleted = sum(client.delete(f"{CACHE_KEY_PREFIX}{cid}") for cid in affected)  # type: ignore
            client.close()
            logger.info("Invalidated %d cached clause payload(s).", deleted)
        except Exception:
            logger.exception("Cache invalidation failed; stale cached payloads may remain.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
