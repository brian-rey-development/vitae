import uuid
from typing import Protocol

from vitae.modules.users.domain.entities import User


class UserRepository(Protocol):
    async def get(self, user_id: uuid.UUID) -> User | None: ...
