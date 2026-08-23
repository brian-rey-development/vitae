import asyncio

from vitae.core.auth import DEV_USER_ID
from vitae.core.db import create_db_engine, create_session_maker
from vitae.core.settings import get_settings
from vitae.users.models import User


async def seed_dev_user() -> None:
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("refusing to seed the dev user in production")

    engine = create_db_engine(settings.database_url)
    session_maker = create_session_maker(engine)
    try:
        async with session_maker() as session:
            if await session.get(User, DEV_USER_ID) is None:
                session.add(User(id=DEV_USER_ID))
                await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_dev_user())
