import uuid
from typing import Protocol

from vitae.modules.users.domain.entities import Profile, User


class UserRepository(Protocol):
    async def get(self, user_id: uuid.UUID) -> User | None: ...


class ProfileRepository(Protocol):
    async def get(self, user_id: uuid.UUID) -> Profile | None: ...

    async def upsert(self, profile: Profile) -> Profile: ...
