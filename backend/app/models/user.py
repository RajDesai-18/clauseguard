"""User model.

Schema is governed by Better Auth's expected shape. Better Auth (running
in Next.js) writes to this table directly; FastAPI only reads from it.
We declare it in SQLAlchemy so Alembic can create the table and so we
can join from Contract.user_id back to the user record.

Reference: https://www.better-auth.com/docs/concepts/database#core-schema
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.contract import Contract


class User(Base):
    """Platform user. Schema mirrors Better Auth's `user` table."""

    __tablename__ = "user"

    # Better Auth uses string IDs (cuid/nanoid), not UUIDs, for its own tables.
    # We follow that convention so Better Auth can manage these rows directly.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # ClauseGuard-specific column. Better Auth ignores unknown columns.
    plan: Mapped[str] = mapped_column(
        String(50), server_default="free", default="free", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    contracts: Mapped[list[Contract]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
