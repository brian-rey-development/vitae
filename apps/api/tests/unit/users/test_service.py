import uuid
from datetime import UTC, datetime

import pytest

from vitae.modules.users.application.service import UserService
from vitae.modules.users.domain.entities import User

pytestmark = pytest.mark.unit


class FakeUserRepository:
    def __init__(self, user: User | None = None) -> None:
        self._user = user

    async def get(self, user_id: uuid.UUID) -> User | None:
        if self._user is not None and self._user.id == user_id:
            return self._user
        return None


async def test_get_user_returns_the_user() -> None:
    user = User(id=uuid.uuid4(), email="a@example.com", created_at=datetime.now(UTC))
    service = UserService(FakeUserRepository(user))

    assert await service.get_user(user.id) == user


async def test_get_user_missing_returns_none() -> None:
    service = UserService(FakeUserRepository())
    assert await service.get_user(uuid.uuid4()) is None
