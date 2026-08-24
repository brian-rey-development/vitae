from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_db_session_maker(request: Request) -> async_sessionmaker[AsyncSession]:
    # app.state is dynamically typed; the app factory sets this at startup (see core/lifespan.py).
    return cast(async_sessionmaker[AsyncSession], request.app.state.db_session_maker)


async def get_db_session(
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(get_db_session_maker)],
) -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
