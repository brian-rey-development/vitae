import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from vitae.core.database import create_db_engine, create_db_session_maker

logger = logging.getLogger("vitae")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings

    engine = create_db_engine(settings.database_url)
    app.state.db_engine = engine
    app.state.db_session_maker = create_db_session_maker(engine)
    logger.info(
        "startup: Vitae API (env=%s, version=%s)", settings.environment, settings.app_version
    )

    yield

    await engine.dispose()
    logger.info("shutdown: Vitae API")
