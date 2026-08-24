import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import PostgresUnitOfWork, SessionDep
from vitae.modules.messages.application.service import MessageService
from vitae.modules.messages.infra.http.schemas import MessageCreate, MessageRead
from vitae.modules.messages.infra.persistence.repository import (
    PostgresConversationOwnership,
    PostgresMessageRepository,
)

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])


def get_message_service(session: SessionDep) -> MessageService:
    return MessageService(
        PostgresMessageRepository(session),
        PostgresConversationOwnership(session),
        PostgresUnitOfWork(session),
    )


ServiceDep = Annotated[MessageService, Depends(get_message_service)]


@router.post("")
async def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    user_id: CurrentUserId,
    service: ServiceDep,
) -> MessageRead:
    """Add a message to a conversation."""
    message = await service.add(conversation_id, user_id, payload.content)
    return MessageRead.model_validate(message)


@router.get("")
async def list_messages(
    conversation_id: uuid.UUID, user_id: CurrentUserId, service: ServiceDep
) -> list[MessageRead]:
    """List a conversation's messages."""
    messages = await service.list_messages(conversation_id, user_id)
    return [MessageRead.model_validate(m) for m in messages]
