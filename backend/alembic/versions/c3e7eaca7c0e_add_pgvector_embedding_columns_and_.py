"""add pgvector embedding columns and clause_templates table

Revision ID: c3e7eaca7c0e
Revises: 7b636a8b845a
Create Date: 2026-04-12 15:13:14.595329
"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e7eaca7c0e'
down_revision: Union[str, Sequence[str], None] = '7b636a8b845a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension (must come before any vector columns)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('clause_templates',
    sa.Column('contract_type', sa.String(length=100), nullable=False),
    sa.Column('clause_type', sa.String(length=100), nullable=False),
    sa.Column('standard_text', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(1536), nullable=False),
    sa.Column('source', sa.String(length=500), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clause_templates_clause_type'), 'clause_templates', ['clause_type'], unique=False)
    op.create_index(op.f('ix_clause_templates_contract_type'), 'clause_templates', ['contract_type'], unique=False)
    op.add_column('clauses', sa.Column('embedding', pgvector.sqlalchemy.Vector(1536), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('clauses', 'embedding')
    op.drop_index(op.f('ix_clause_templates_contract_type'), table_name='clause_templates')
    op.drop_index(op.f('ix_clause_templates_clause_type'), table_name='clause_templates')
    op.drop_table('clause_templates')
    op.execute("DROP EXTENSION IF EXISTS vector")