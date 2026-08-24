import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import SessionDep, SqlUnitOfWork
from vitae.core.errors import NotFoundError
from vitae.modules.conversations.application.services import ConversationService
from vitae.modules.conversations.domain.entities import Conversation
from vitae.modules.conversations.domain.enums import MessageRole
from vitae.modules.conversations.infra.http.schemas import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from vitae.modules.conversations.infra.persistence.repository import (
    SqlConversationRepository,
    SqlMessageRepository,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(session: SessionDep) -> ConversationService:
    return ConversationService(
        SqlConversationRepository(session),
        SqlMessageRepository(session),
        SqlUnitOfWork(session),
    )


ServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


async def get_owned_conversation(
    conversation_id: uuid.UUID, user_id: CurrentUserId, service: ServiceDep
) -> Conversation:
    conversation = await service.get(conversation_id, user_id)
    if conversation is None:
        raise NotFoundError("conversation not found")
    return conversation


OwnedConversation = Annotated[Conversation, Depends(get_owned_conversation)]


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


@router.post("/{conversation_id}/messages")
async def create_message(
    payload: MessageCreate, conversation: OwnedConversation, service: ServiceDep
) -> MessageRead:
    """Add a message to a conversation."""
    message = await service.add_message(conversation.id, MessageRole.user, payload.content)
    return MessageRead.model_validate(message)


@router.get("/{conversation_id}/messages")
async def list_messages(conversation: OwnedConversation, service: ServiceDep) -> list[MessageRead]:
    """List a conversation's messages."""
    messages = await service.list_messages(conversation.id)
    return [MessageRead.model_validate(m) for m in messages]
