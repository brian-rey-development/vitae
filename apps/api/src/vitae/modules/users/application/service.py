import uuid

from vitae.modules.users.domain.entities import User
from vitae.modules.users.domain.ports import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self._repository.get(user_id)
