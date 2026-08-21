from fastapi import APIRouter, FastAPI

from vitae.health.router import router as health_router
from vitae.meta.router import router as meta_router


def register_routers(app: FastAPI, api_v1_prefix: str) -> None:
    """Single composition point for every domain router.

    Ops endpoints (health) stay unversioned; product endpoints live under the
    versioned prefix. Core must not import domains, so all wiring happens here.
    """
    app.include_router(health_router)

    v1 = APIRouter(prefix=api_v1_prefix)
    v1.include_router(meta_router)
    # future domains mount here: v1.include_router(checkins_router), etc.
    app.include_router(v1)
