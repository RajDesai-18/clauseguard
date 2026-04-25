"""Dependency injection for API endpoints."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.auth import Session as AuthSession
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_optional_user(
    db: DBSession,
    better_auth_session_token: Annotated[
        str | None, Cookie(alias="better-auth.session_token")
    ] = None,
) -> User | None:
    """Resolve the current user from the Better Auth session cookie.

    Returns None when no valid session is present. Use this for endpoints
    that work for both authenticated and anonymous callers. For endpoints
    that require a user, use `get_current_user` instead.

    The cookie value Better Auth sets is `<token>.<signature>`. We split
    on `.` and use the token portion to look up the session row.
    """
    if better_auth_session_token is None:
        return None

    # Better Auth signs the cookie value: format is "<token>.<signature>".
    # We only need the token to look up the session row.
    raw_token = better_auth_session_token.split(".", 1)[0]
    if not raw_token:
        return None

    result = await db.execute(
        select(AuthSession, User)
        .join(User, AuthSession.user_id == User.id)
        .where(AuthSession.token == raw_token)
    )
    row = result.one_or_none()
    if row is None:
        return None

    auth_session, user = row

    # Reject expired sessions. Better Auth refreshes sessions on use,
    # but we still validate server-side.
    if auth_session.expires_at < datetime.now(UTC):
        return None

    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    """Resolve the current user from the session cookie.

    Raises 401 if no valid session is present. Use this on every endpoint
    that operates on user-scoped data (contracts, clauses, settings).
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
