import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.core.db import get_session

logger = logging.getLogger("vitae")

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get("/health/live")
async def live() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/health/ready")
async def ready(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthStatus:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return HealthStatus(status="ready")
