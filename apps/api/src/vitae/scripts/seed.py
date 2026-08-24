import asyncio

from vitae.core.auth import DEV_USER_ID
from vitae.core.config import get_settings
from vitae.core.database import create_db_engine, create_db_session_maker
from vitae.modules.users.infra.persistence.models import UserModel


async def seed_dev_user() -> None:
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("refusing to seed the dev user in production")

    engine = create_db_engine(settings.database_url)
    session_maker = create_db_session_maker(engine)
    try:
        async with session_maker() as session:
            if await session.get(UserModel, DEV_USER_ID) is None:
                session.add(UserModel(id=DEV_USER_ID, email="dev@example.com"))
                await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_dev_user())
