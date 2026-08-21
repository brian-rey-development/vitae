import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("vitae")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    logger.info(
        "startup: Vitae API (env=%s, version=%s)", settings.environment, settings.app_version
    )
    # M2 will open the database connection pool here and store it on app.state.
    yield
    # M2 will close the database connection pool here.
    logger.info("shutdown: Vitae API")
