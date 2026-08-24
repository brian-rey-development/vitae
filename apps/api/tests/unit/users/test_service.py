import uuid
from datetime import UTC, date, datetime

import pytest

from vitae.modules.users.application.services import ProfileService, UserService
from vitae.modules.users.domain.entities import Profile, User
from vitae.modules.users.domain.enums import Sex

pytestmark = pytest.mark.unit


class FakeUserRepository:
    def __init__(self, user: User | None = None) -> None:
        self._user = user

    async def get(self, user_id: uuid.UUID) -> User | None:
        if self._user is not None and self._user.id == user_id:
            return self._user
        return None


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


async def test_get_user_returns_the_user() -> None:
    user = User(id=uuid.uuid4(), email="a@vitae.local", created_at=datetime.now(UTC))
    service = UserService(FakeUserRepository(user))

    assert await service.get_user(user.id) == user


async def test_get_user_missing_returns_none() -> None:
    service = UserService(FakeUserRepository())
    assert await service.get_user(uuid.uuid4()) is None


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


async def test_update_profile_is_idempotent() -> None:
    uow = FakeUnitOfWork()
    service = ProfileService(FakeProfileRepository(), uow)
    user_id = uuid.uuid4()

    await service.update_profile(user_id, display_name="A", date_of_birth=None, sex=None)
    profile = await service.update_profile(user_id, display_name="B", date_of_birth=None, sex=None)

    assert profile.display_name == "B"
    assert uow.commits == 2
