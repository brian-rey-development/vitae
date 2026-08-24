from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import SessionDep, SqlUnitOfWork
from vitae.core.errors import NotFoundError
from vitae.modules.users.application.services import ProfileService
from vitae.modules.users.infra.http.schemas import ProfileRead, ProfileUpdate
from vitae.modules.users.infra.persistence.repository import SqlProfileRepository

router = APIRouter(prefix="/me", tags=["users"])


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(SqlProfileRepository(session), SqlUnitOfWork(session))


ServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


@router.get("/profile")
async def get_profile(user_id: CurrentUserId, service: ServiceDep) -> ProfileRead:
    """Get the current user's profile."""
    profile = await service.get_profile(user_id)
    if profile is None:
        raise NotFoundError("profile not set")
    return ProfileRead.model_validate(profile)


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate, user_id: CurrentUserId, service: ServiceDep
) -> ProfileRead:
    """Create or update the current user's profile."""
    profile = await service.update_profile(
        user_id,
        display_name=payload.display_name,
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
    )
    return ProfileRead.model_validate(profile)
