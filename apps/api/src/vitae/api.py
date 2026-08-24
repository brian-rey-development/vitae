from fastapi import APIRouter, FastAPI

from vitae.modules.conversations.infra.http.router import router as conversations_router
from vitae.modules.users.infra.http.router import router as users_router
from vitae.platform.health import router as health_router
from vitae.platform.meta import router as meta_router


def register_routers(app: FastAPI, api_v1_prefix: str) -> None:
    app.include_router(health_router)

    v1 = APIRouter(prefix=api_v1_prefix)
    v1.include_router(meta_router)
    v1.include_router(users_router)
    v1.include_router(conversations_router)
    app.include_router(v1)
