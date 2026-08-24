from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import PostgresUnitOfWork, SessionDep
from vitae.core.errors import NotFoundError
from vitae.modules.users.application.services import ProfileService, UserService
from vitae.modules.users.infra.http.schemas import MeRead, ProfileRead, ProfileUpdate
from vitae.modules.users.infra.persistence.repository import (
    PostgresProfileRepository,
    PostgresUserRepository,
)

router = APIRouter(prefix="/me", tags=["users"])


def get_user_service(session: SessionDep) -> UserService:
    return UserService(PostgresUserRepository(session))


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(PostgresProfileRepository(session), PostgresUnitOfWork(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


@router.get("")
async def get_me(
    user_id: CurrentUserId, users: UserServiceDep, profiles: ProfileServiceDep
) -> MeRead:
    """Get the current user's account and profile."""
    user = await users.get_user(user_id)
    if user is None:
        raise NotFoundError("user not found")
    profile = await profiles.get_profile(user_id)
    return MeRead(
        email=user.email,
        profile=ProfileRead.model_validate(profile) if profile is not None else None,
    )


@router.get("/profile")
async def get_profile(user_id: CurrentUserId, service: ProfileServiceDep) -> ProfileRead:
    """Get the current user's profile."""
    profile = await service.get_profile(user_id)
    if profile is None:
        raise NotFoundError("profile not set")
    return ProfileRead.model_validate(profile)


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate, user_id: CurrentUserId, service: ProfileServiceDep
) -> ProfileRead:
    """Create or update the current user's profile."""
    profile = await service.update_profile(
        user_id,
        display_name=payload.display_name,
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
    )
    return ProfileRead.model_validate(profile)
