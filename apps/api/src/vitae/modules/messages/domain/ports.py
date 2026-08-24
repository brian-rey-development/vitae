import uuid
from typing import Protocol

from vitae.modules.messages.domain.entities import Message


class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...

    async def list_all(self, conversation_id: uuid.UUID) -> list[Message]: ...


class ConversationOwnership(Protocol):
    async def is_owned_by(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool: ...
