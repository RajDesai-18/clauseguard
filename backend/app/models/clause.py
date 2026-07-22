"""Clause model."""

from __future__ import annotations

from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.contract import Contract  # noqa: F401


class Clause(Base, UUIDMixin, TimestampMixin):
    """Individual clause extracted from a contract.

    Analysis-derived fields (`risk_level`, `explanation`, `confidence`) are
    nullable by design: the pipeline inserts a clause row as soon as its text
    is split out, then populates the risk assessment in a later step. A clause
    can therefore legitimately exist with these unset while analysis is still
    in flight, so the schema must permit nulls here. The API response schema
    and the frontend client both treat them as nullable to match.
    """

    __tablename__ = "clauses"

    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_comparison: Mapped[str | None] = mapped_column(Text)
    suggested_redline: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, default=0.0, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    contract: Mapped[Contract] = relationship(back_populates="clauses")

    def __repr__(self) -> str:
        return f"<Clause {self.clause_type} [{self.risk_level}]>"
