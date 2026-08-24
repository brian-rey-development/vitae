import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.modules.profiles.domain.entities import Profile
from vitae.modules.profiles.infra.persistence.mappers import to_profile
from vitae.modules.profiles.infra.persistence.models import ProfileModel


class PostgresProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        model = await self._session.get(ProfileModel, user_id)
        if model is None:
            return None
        return to_profile(model)

    async def upsert(self, profile: Profile) -> Profile:
        fields = {
            "display_name": profile.display_name,
            "date_of_birth": profile.date_of_birth,
            "sex": profile.sex,
        }
        statement = (
            insert(ProfileModel)
            .values(user_id=profile.user_id, **fields)
            .on_conflict_do_update(
                index_elements=[ProfileModel.user_id],
                set_={**fields, "updated_at": func.now()},
            )
            .returning(ProfileModel)
        )
        result = await self._session.execute(statement)
        return to_profile(result.scalar_one())
