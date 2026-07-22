"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import settings
from app.models import Base  # noqa: F401 -- registers all models

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# Tables whose schema is owned and managed by Better Auth (running in the
# Next.js app), not by us. Our SQLAlchemy mirror in `app/models/auth.py`
# exists only so Alembic can create these at baseline and so `Contract` can
# join to `user`; it is not an authoritative description of their columns.
BETTER_AUTH_TABLES = frozenset({"user", "session", "account", "verification"})


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Filter objects out of Alembic autogenerate comparison.

    Excludes the Better Auth-managed tables (and everything under them) so
    autogenerate stops proposing spurious alters against schema we deliberately
    do not own. Better Auth uses TEXT where our mirror declares VARCHAR, for
    example, which otherwise produces a stream of VARCHAR->TEXT alters on every
    autogenerate run.

    This only affects autogenerate diffing. It does not change the existing
    baseline migration that creates these tables, nor does it prevent hand
    written migrations from touching them if ever needed.

    Args:
        object_: The schema object being considered (Table, Column, Index, ...).
        name: The object's name, or None.
        type_: The kind of object ("table", "column", "index", ...).
        reflected: True if the object came from database reflection.
        compare_to: The object being compared against, or None.

    Returns:
        False to exclude the object from comparison, True to include it.
    """
    if type_ == "table":
        return name not in BETTER_AUTH_TABLES
    # Columns, indexes, and constraints carry a reference to their parent
    # table; exclude anything owned by a Better Auth table.
    parent_table = getattr(object_, "table", None)
    return parent_table is None or parent_table.name not in BETTER_AUTH_TABLES


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Execute migrations against a live connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in online mode with async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),  # type: ignore[arg-type]
        poolclass=None,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
