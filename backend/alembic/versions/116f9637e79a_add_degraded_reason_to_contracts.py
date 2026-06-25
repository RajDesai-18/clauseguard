"""add degraded_reason to contracts

Revision ID: 116f9637e79a
Revises: 427c7b4e136f
Create Date: 2026-06-24 21:52:40.208943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '116f9637e79a'
down_revision: Union[str, Sequence[str], None] = '427c7b4e136f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contracts",
        sa.Column("degraded_reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contracts", "degraded_reason")