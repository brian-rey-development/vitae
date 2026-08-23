from fastapi import APIRouter

from vitae.core.auth import CurrentUserId
from vitae.core.db import SessionDep
from vitae.core.errors import NotFoundError
from vitae.users.repository import ProfileRepository
from vitae.users.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/me", tags=["users"])


@router.get("/profile")
async def get_profile(user_id: CurrentUserId, session: SessionDep) -> ProfileRead:
    profile = await ProfileRepository(session).get(user_id)
    if profile is None:
        raise NotFoundError("profile not set")
    return ProfileRead.model_validate(profile)


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate, user_id: CurrentUserId, session: SessionDep
) -> ProfileRead:
    profile = await ProfileRepository(session).upsert(
        user_id,
        display_name=payload.display_name,
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
    )
    await session.commit()
    return ProfileRead.model_validate(profile)
