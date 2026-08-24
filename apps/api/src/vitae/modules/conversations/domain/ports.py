import uuid
from typing import Protocol

from vitae.modules.conversations.domain.entities import Conversation


class ConversationRepository(Protocol):
    async def add(self, conversation: Conversation) -> None: ...

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None: ...

    async def list_all(self, user_id: uuid.UUID) -> list[Conversation]: ...
