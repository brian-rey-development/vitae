from fastapi import APIRouter, FastAPI

from vitae.modules.conversations.infra.http.router import router as conversations_router
from vitae.modules.messages.infra.http.router import router as messages_router
from vitae.modules.profiles.infra.http.router import router as profiles_router
from vitae.modules.users.infra.http.router import router as users_router
from vitae.platform.health import router as health_router
from vitae.platform.meta import router as meta_router


def register_routers(app: FastAPI, api_v1_prefix: str) -> None:
    app.include_router(health_router)

    v1 = APIRouter(prefix=api_v1_prefix)
    v1.include_router(meta_router)
    v1.include_router(users_router)
    v1.include_router(profiles_router)
    v1.include_router(conversations_router)
    v1.include_router(messages_router)
    app.include_router(v1)
