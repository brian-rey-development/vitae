import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import PostgresUnitOfWork, SessionDep
from vitae.core.errors import NotFoundError
from vitae.modules.conversations.application.service import ConversationService
from vitae.modules.conversations.infra.http.schemas import ConversationCreate, ConversationRead
from vitae.modules.conversations.infra.persistence.repository import PostgresConversationRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(session: SessionDep) -> ConversationService:
    return ConversationService(PostgresConversationRepository(session), PostgresUnitOfWork(session))


ServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


@router.post("")
async def create_conversation(
    payload: ConversationCreate, user_id: CurrentUserId, service: ServiceDep
) -> ConversationRead:
    """Create a conversation for the current user."""
    conversation = await service.create(user_id, payload.title)
    return ConversationRead.model_validate(conversation)


@router.get("")
async def list_conversations(user_id: CurrentUserId, service: ServiceDep) -> list[ConversationRead]:
    """List the current user's conversations."""
    conversations = await service.list_conversations(user_id)
    return [ConversationRead.model_validate(c) for c in conversations]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID, user_id: CurrentUserId, service: ServiceDep
) -> ConversationRead:
    """Get one of the current user's conversations."""
    conversation = await service.get(conversation_id, user_id)
    if conversation is None:
        raise NotFoundError("conversation not found")
    return ConversationRead.model_validate(conversation)
