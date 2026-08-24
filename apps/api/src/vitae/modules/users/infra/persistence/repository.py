import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from vitae.modules.users.domain.entities import User
from vitae.modules.users.infra.persistence.mappers import to_user
from vitae.modules.users.infra.persistence.models import UserModel


class PostgresUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None
        return to_user(model)
