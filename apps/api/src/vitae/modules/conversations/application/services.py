import uuid
from datetime import UTC, datetime

from vitae.core.database import UnitOfWork
from vitae.modules.conversations.domain.entities import Conversation, Message
from vitae.modules.conversations.domain.enums import MessageRole
from vitae.modules.conversations.domain.ports import ConversationRepository, MessageRepository


class ConversationService:
    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        uow: UnitOfWork,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._uow = uow

    async def create(self, user_id: uuid.UUID, title: str | None) -> Conversation:
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
            created_at=datetime.now(UTC),
        )
        await self._conversations.add(conversation)
        await self._uow.commit()
        return conversation

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        return await self._conversations.get(conversation_id, user_id)

    async def list_conversations(self, user_id: uuid.UUID) -> list[Conversation]:
        return await self._conversations.list_all(user_id)

    async def add_message(
        self, conversation_id: uuid.UUID, role: MessageRole, content: str
    ) -> Message:
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.now(UTC),
        )
        await self._messages.add(message)
        await self._uow.commit()
        return message

    async def list_messages(self, conversation_id: uuid.UUID) -> list[Message]:
        return await self._messages.list_all(conversation_id)
