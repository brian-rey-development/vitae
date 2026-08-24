import uuid

import pytest

from vitae.core.errors import NotFoundError
from vitae.modules.messages.application.service import MessageService
from vitae.modules.messages.domain.entities import Message
from vitae.modules.messages.domain.enums import MessageRole

pytestmark = pytest.mark.unit


class FakeMessageRepository:
    def __init__(self) -> None:
        self._items: list[Message] = []

    async def add(self, message: Message) -> None:
        self._items.append(message)

    async def list_all(self, conversation_id: uuid.UUID) -> list[Message]:
        return [m for m in self._items if m.conversation_id == conversation_id]


class FakeConversationOwnership:
    def __init__(self, owned: bool) -> None:
        self._owned = owned

    async def is_owned_by(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self._owned


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


async def test_add_message_commits_and_lists() -> None:
    uow = FakeUnitOfWork()
    service = MessageService(FakeMessageRepository(), FakeConversationOwnership(owned=True), uow)
    conversation_id = uuid.uuid4()
    user_id = uuid.uuid4()

    message = await service.add(conversation_id, user_id, "hi")

    assert message.role is MessageRole.user
    assert uow.commits == 1
    listed = await service.list_messages(conversation_id, user_id)
    assert [m.content for m in listed] == ["hi"]


async def test_add_to_unowned_conversation_is_rejected() -> None:
    service = MessageService(
        FakeMessageRepository(), FakeConversationOwnership(owned=False), FakeUnitOfWork()
    )

    with pytest.raises(NotFoundError):
        await service.add(uuid.uuid4(), uuid.uuid4(), "hi")


async def test_list_on_unowned_conversation_is_rejected() -> None:
    service = MessageService(
        FakeMessageRepository(), FakeConversationOwnership(owned=False), FakeUnitOfWork()
    )

    with pytest.raises(NotFoundError):
        await service.list_messages(uuid.uuid4(), uuid.uuid4())
