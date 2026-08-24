import uuid
from datetime import UTC, datetime

from vitae.core.database import UnitOfWork
from vitae.modules.conversations.domain.entities import Conversation
from vitae.modules.conversations.domain.ports import ConversationRepository


class ConversationService:
    def __init__(self, repository: ConversationRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    async def create(self, user_id: uuid.UUID, title: str | None) -> Conversation:
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
            created_at=datetime.now(UTC),
        )
        await self._repository.add(conversation)
        await self._uow.commit()
        return conversation

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        return await self._repository.get(conversation_id, user_id)

    async def list_conversations(self, user_id: uuid.UUID) -> list[Conversation]:
        return await self._repository.list_all(user_id)
