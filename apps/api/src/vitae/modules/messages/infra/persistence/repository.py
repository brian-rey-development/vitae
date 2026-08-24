import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.modules.messages.domain.entities import Message
from vitae.modules.messages.infra.persistence.mappers import to_message, to_message_model
from vitae.modules.messages.infra.persistence.models import MessageModel


class PostgresMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> None:
        self._session.add(to_message_model(message))
        await self._session.flush()

    async def list_all(self, conversation_id: uuid.UUID) -> list[Message]:
        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
        )
        return [to_message(model) for model in result.scalars().all()]


class PostgresConversationOwnership:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_owned_by(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        # Reads the conversations table by name (an allowed foreign-key reference)
        # so the messages module never imports the conversations module.
        result = await self._session.execute(
            text("SELECT 1 FROM conversations WHERE id = :conversation_id AND user_id = :user_id"),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
        return result.first() is not None
