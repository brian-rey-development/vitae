import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.users.models import Profile, Sex


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        return await self._session.get(Profile, user_id)

    async def upsert(
        self,
        user_id: uuid.UUID,
        *,
        display_name: str | None,
        date_of_birth: date | None,
        sex: Sex | None,
    ) -> Profile:
        fields = {"display_name": display_name, "date_of_birth": date_of_birth, "sex": sex}
        statement = (
            insert(Profile)
            .values(user_id=user_id, **fields)
            .on_conflict_do_update(
                index_elements=[Profile.user_id],
                set_={**fields, "updated_at": func.now()},
            )
            .returning(Profile)
        )
        result = await self._session.execute(statement)
        return result.scalar_one()
