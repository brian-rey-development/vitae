import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from vitae.core.db import SessionDep

logger = logging.getLogger("vitae")

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get("/health/live")
async def live() -> HealthStatus:
    """Liveness probe: the process is up. Does not touch the datastore."""
    return HealthStatus(status="ok")


@router.get("/health/ready")
async def ready(session: SessionDep) -> HealthStatus:
    """Readiness probe: the datastore is reachable."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return HealthStatus(status="ready")
