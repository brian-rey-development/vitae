import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vitae.core.app import create_app
from vitae.core.auth import DEV_USER_ID
from vitae.core.config import get_settings
from vitae.core.database import Base, get_db_session
from vitae.modules.conversations.infra.persistence import (
    models as _conversation_models,  # noqa: F401
)
from vitae.modules.users.infra.persistence import models as _user_models  # noqa: F401
from vitae.modules.users.infra.persistence.models import UserModel

TEST_DB_NAME = "vitae_test"


def _test_database_url() -> str:
    base = get_settings().database_url
    return f"{base.rsplit('/', 1)[0]}/{TEST_DB_NAME}"


async def _prepare_database() -> None:
    admin = create_async_engine(get_settings().database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        await connection.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    await admin.dispose()

    engine = create_async_engine(_test_database_url())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        session.add(UserModel(id=DEV_USER_ID))
        await session.commit()
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _database_ready() -> None:
    asyncio.run(_prepare_database())


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(_test_database_url())
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def _use_test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _use_test_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
