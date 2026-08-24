import uuid
from datetime import date

import pytest

from vitae.modules.profiles.application.service import ProfileService
from vitae.modules.profiles.domain.entities import Profile
from vitae.modules.profiles.domain.enums import Sex

pytestmark = pytest.mark.unit


class FakeProfileRepository:
    def __init__(self) -> None:
        self._items: dict[uuid.UUID, Profile] = {}

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        return self._items.get(user_id)

    async def upsert(self, profile: Profile) -> Profile:
        self._items[profile.user_id] = profile
        return profile


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


async def test_update_profile_upserts_and_commits() -> None:
    uow = FakeUnitOfWork()
    service = ProfileService(FakeProfileRepository(), uow)
    user_id = uuid.uuid4()

    profile = await service.update_profile(
        user_id, display_name="Bri", date_of_birth=date(1995, 3, 10), sex=Sex.male
    )

    assert profile.display_name == "Bri"
    assert uow.commits == 1
    assert await service.get_profile(user_id) == profile


async def test_get_profile_missing_returns_none() -> None:
    service = ProfileService(FakeProfileRepository(), FakeUnitOfWork())
    assert await service.get_profile(uuid.uuid4()) is None
