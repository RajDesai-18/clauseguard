"""ClauseTemplate model for market-standard clause comparison."""

from __future__ import annotations

from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ClauseTemplate(Base, UUIDMixin, TimestampMixin):
    """Market-standard clause templates for risk comparison.

    Pre-embedded standard clauses used for similarity search
    during risk scoring. Comparing uploaded clauses against these
    templates provides grounded, consistent risk assessment.
    """

    __tablename__ = "clause_templates"

    contract_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<ClauseTemplate {self.contract_type}/{self.clause_type}>"
