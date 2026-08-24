import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vitae.modules.conversations.domain.entities import Conversation
from vitae.modules.conversations.infra.persistence.mappers import (
    to_conversation,
    to_conversation_model,
)
from vitae.modules.conversations.infra.persistence.models import ConversationModel


class PostgresConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        self._session.add(to_conversation_model(conversation))
        await self._session.flush()

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id)
        if model is None or model.user_id != user_id:
            return None
        return to_conversation(model)

    async def list_all(self, user_id: uuid.UUID) -> list[Conversation]:
        result = await self._session.execute(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
        )
        return [to_conversation(model) for model in result.scalars().all()]
