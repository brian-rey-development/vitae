from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get("/health")
def health() -> HealthStatus:
    return HealthStatus(status="ok")
