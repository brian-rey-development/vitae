import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.conversations.models import Conversation, Message, MessageRole


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: uuid.UUID, title: str | None) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        conversation = await self._session.get(Conversation, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return conversation

    async def list(self, user_id: uuid.UUID) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
        return list(result.scalars().all())


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation_id: uuid.UUID, role: MessageRole, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self._session.add(message)
        await self._session.flush()
        return message

    async def list(self, conversation_id: uuid.UUID) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
