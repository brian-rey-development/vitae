import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def create_db_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_db_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def get_db_session_maker(request: Request) -> async_sessionmaker[AsyncSession]:
    # app.state is dynamically typed; the app factory sets this at startup (see core/lifespan.py).
    return cast(async_sessionmaker[AsyncSession], request.app.state.db_session_maker)


async def get_db_session(
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(get_db_session_maker)],
) -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
