"""Alembic env.py — async migration runner."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models.database import Base

# Import all models so Base.metadata is populated
from app.models.employee import CostCenter, Employee  # noqa: F401
from app.models.expense import ExpenseReport, LineItem, PolicyViolation, Receipt  # noqa: F401
from app.models.approval import ActionToken, ApprovalAction  # noqa: F401
from app.models.policy import ApprovalThreshold, ExpenseCategory, PerDiemRate  # noqa: F401
from app.models.notification import Notification, WorkdaySyncLog  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
