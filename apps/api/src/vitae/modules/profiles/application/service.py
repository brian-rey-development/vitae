import uuid
from datetime import date

from vitae.core.database import UnitOfWork
from vitae.modules.profiles.domain.entities import Profile
from vitae.modules.profiles.domain.enums import Sex
from vitae.modules.profiles.domain.ports import ProfileRepository


class ProfileService:
    def __init__(self, repository: ProfileRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    async def get_profile(self, user_id: uuid.UUID) -> Profile | None:
        return await self._repository.get(user_id)

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
        saved = await self._repository.upsert(profile)
        await self._uow.commit()
        return saved
