import uuid

import pytest

from vitae.modules.conversations.application.service import ConversationService
from vitae.modules.conversations.domain.entities import Conversation

pytestmark = pytest.mark.unit


class FakeConversationRepository:
    def __init__(self) -> None:
        self._items: dict[uuid.UUID, Conversation] = {}

    async def add(self, conversation: Conversation) -> None:
        self._items[conversation.id] = conversation

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        conversation = self._items.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return conversation

    async def list_all(self, user_id: uuid.UUID) -> list[Conversation]:
        return [c for c in self._items.values() if c.user_id == user_id]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


async def test_create_persists_and_commits() -> None:
    uow = FakeUnitOfWork()
    service = ConversationService(FakeConversationRepository(), uow)
    user_id = uuid.uuid4()

    conversation = await service.create(user_id, "morning")

    assert conversation.title == "morning"
    assert conversation.user_id == user_id
    assert uow.commits == 1
    assert await service.get(conversation.id, user_id) == conversation


async def test_get_is_scoped_to_owner() -> None:
    service = ConversationService(FakeConversationRepository(), FakeUnitOfWork())
    conversation = await service.create(uuid.uuid4(), "mine")

    assert await service.get(conversation.id, uuid.uuid4()) is None
