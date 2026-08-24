import uuid
from typing import Protocol

from vitae.modules.profiles.domain.entities import Profile


class ProfileRepository(Protocol):
    async def get(self, user_id: uuid.UUID) -> Profile | None: ...

    async def upsert(self, profile: Profile) -> Profile: ...
