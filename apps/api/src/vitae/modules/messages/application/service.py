import uuid
from datetime import UTC, datetime

from vitae.core.database import UnitOfWork
from vitae.core.errors import NotFoundError
from vitae.modules.messages.domain.entities import Message
from vitae.modules.messages.domain.enums import MessageRole
from vitae.modules.messages.domain.ports import ConversationOwnership, MessageRepository


class MessageService:
    def __init__(
        self,
        repository: MessageRepository,
        conversation_ownership: ConversationOwnership,
        uow: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._conversation_ownership = conversation_ownership
        self._uow = uow

    async def add(self, conversation_id: uuid.UUID, user_id: uuid.UUID, content: str) -> Message:
        await self._require_owned_conversation(conversation_id, user_id)
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=MessageRole.user,
            content=content,
            created_at=datetime.now(UTC),
        )
        await self._repository.add(message)
        await self._uow.commit()
        return message

    async def list_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> list[Message]:
        await self._require_owned_conversation(conversation_id, user_id)
        return await self._repository.list_all(conversation_id)

    async def _require_owned_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        if not await self._conversation_ownership.is_owned_by(conversation_id, user_id):
            raise NotFoundError("conversation not found")
