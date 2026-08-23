from fastapi import FastAPI

from vitae.api import register_routers
from vitae.core.config import Settings, get_settings
from vitae.core.errors import register_error_handlers
from vitae.core.lifespan import lifespan

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {"name": "meta", "description": "Application metadata."},
    {"name": "users", "description": "The current user and their profile."},
    {"name": "conversations", "description": "Conversations and their messages."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = settings

    register_error_handlers(app)
    register_routers(app, settings.api_v1_prefix)

    return app
