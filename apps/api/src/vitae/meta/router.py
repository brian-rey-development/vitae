from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from vitae.core.settings import Settings, get_settings

router = APIRouter(tags=["meta"])


class MetaInfo(BaseModel):
    app_name: str
    environment: str
    is_production: bool


@router.get("/meta")
def meta(settings: Annotated[Settings, Depends(get_settings)]) -> MetaInfo:
    """Application metadata (name, environment)."""
    return MetaInfo(
        app_name=settings.app_name,
        environment=settings.environment,
        is_production=settings.is_production,
    )
