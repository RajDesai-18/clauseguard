"""make clause risk_level and confidence nullable

Revision ID: 77fa49444bdb
Revises: 5d635143e834
Create Date: 2026-04-26 00:51:55.324265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77fa49444bdb'
down_revision: Union[str, Sequence[str], None] = '5d635143e834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make risk_level and confidence nullable.

    The saga refactor inverts the clause lifecycle: rows are now
    created by the classify task before analysis runs, so risk_level
    and confidence don't exist until analyze_one_clause_task fills
    them in. The schema must allow that intermediate state.
    """
    op.alter_column(
        "clauses",
        "risk_level",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.alter_column(
        "clauses",
        "confidence",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    """Restore the original NOT NULL constraints.

    Note: this downgrade will fail if any clause rows exist with
    null risk_level or confidence values. That's intentional; the
    constraint can't be re-applied without those rows being either
    backfilled or deleted first.
    """
    op.alter_column(
        "clauses",
        "risk_level",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.alter_column(
        "clauses",
        "confidence",
        existing_type=sa.Float(),
        nullable=False,
    )