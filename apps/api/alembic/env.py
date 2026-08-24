import asyncio
from collections.abc import Iterable
from logging.config import fileConfig

from alembic import context
from alembic.operations import MigrationScript
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from vitae.core.config import get_settings
from vitae.core.database import Base
from vitae.modules.conversations.infra.persistence import (
    models as conversation_models,  # noqa: F401
)
from vitae.modules.messages.infra.persistence import models as message_models  # noqa: F401
from vitae.modules.profiles.infra.persistence import models as profile_models  # noqa: F401
from vitae.modules.users.infra.persistence import models as user_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_REVISION_ID_WIDTH = 4


def use_sequential_revision_id(
    migration_context: MigrationContext,
    revision: Iterable[str | None],
    directives: list[MigrationScript],
) -> None:
    if not directives:
        return
    head = ScriptDirectory.from_config(context.config).get_current_head()
    next_number = 1 if head is None else int(head) + 1
    directives[0].rev_id = f"{next_number:0{_REVISION_ID_WIDTH}d}"


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=use_sequential_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        process_revision_directives=use_sequential_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
