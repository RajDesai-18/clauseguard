"""make clause explanation nullable

Revision ID: 427c7b4e136f
Revises: 77fa49444bdb
Create Date: 2026-04-26 00:53:51.307700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '427c7b4e136f'
down_revision: Union[str, Sequence[str], None] = '77fa49444bdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make explanation nullable.

    Companion to the previous migration. The classify task creates
    clause rows before analysis runs, so explanation is null until
    analyze_one_clause_task fills it in.
    """
    op.alter_column(
        "clauses",
        "explanation",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    """Restore the original NOT NULL constraint on explanation."""
    op.alter_column(
        "clauses",
        "explanation",
        existing_type=sa.Text(),
        nullable=False,
    )