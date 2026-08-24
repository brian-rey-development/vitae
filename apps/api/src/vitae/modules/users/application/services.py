import uuid
from datetime import date

from vitae.core.database import UnitOfWork
from vitae.modules.users.domain.entities import Profile
from vitae.modules.users.domain.enums import Sex
from vitae.modules.users.domain.ports import ProfileRepository


class ProfileService:
    def __init__(self, profiles: ProfileRepository, uow: UnitOfWork) -> None:
        self._profiles = profiles
        self._uow = uow

    async def get_profile(self, user_id: uuid.UUID) -> Profile | None:
        return await self._profiles.get(user_id)

    async def update_profile(
        self,
        user_id: uuid.UUID,
        *,
        display_name: str | None,
        date_of_birth: date | None,
        sex: Sex | None,
    ) -> Profile:
        profile = Profile(
            user_id=user_id,
            display_name=display_name,
            date_of_birth=date_of_birth,
            sex=sex,
        )
        saved = await self._profiles.upsert(profile)
        await self._uow.commit()
        return saved
