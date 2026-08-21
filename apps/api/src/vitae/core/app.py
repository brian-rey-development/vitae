from fastapi import FastAPI

from vitae.core.settings import Settings, get_settings
from vitae.health.router import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(health_router)

    return app
