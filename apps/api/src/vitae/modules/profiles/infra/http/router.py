from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import PostgresUnitOfWork, SessionDep
from vitae.core.errors import NotFoundError
from vitae.modules.profiles.application.service import ProfileService
from vitae.modules.profiles.infra.http.schemas import ProfileRead, ProfileUpdate
from vitae.modules.profiles.infra.persistence.repository import PostgresProfileRepository

router = APIRouter(prefix="/me/profile", tags=["profiles"])


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(PostgresProfileRepository(session), PostgresUnitOfWork(session))


ServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


@router.get("")
async def get_profile(user_id: CurrentUserId, service: ServiceDep) -> ProfileRead:
    """Get the current user's profile."""
    profile = await service.get_profile(user_id)
    if profile is None:
        raise NotFoundError("profile not set")
    return ProfileRead.model_validate(profile)


@router.put("")
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
