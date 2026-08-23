import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.conversations.models import Conversation, MessageRole
from vitae.conversations.repository import ConversationRepository, MessageRepository
from vitae.conversations.schemas import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from vitae.core.auth import CurrentUserId
from vitae.core.db import SessionDep
from vitae.core.errors import NotFoundError

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def get_owned_conversation(
    conversation_id: uuid.UUID, user_id: CurrentUserId, session: SessionDep
) -> Conversation:
    conversation = await ConversationRepository(session).get(conversation_id, user_id)
    if conversation is None:
        raise NotFoundError("conversation not found")
    return conversation


OwnedConversation = Annotated[Conversation, Depends(get_owned_conversation)]


@router.post("")
async def create_conversation(
    payload: ConversationCreate, user_id: CurrentUserId, session: SessionDep
) -> ConversationRead:
    """Create a conversation for the current user."""
    conversation = await ConversationRepository(session).create(user_id, payload.title)
    await session.commit()
    return ConversationRead.model_validate(conversation)


@router.get("")
async def list_conversations(user_id: CurrentUserId, session: SessionDep) -> list[ConversationRead]:
    """List the current user's conversations."""
    conversations = await ConversationRepository(session).list(user_id)
    return [ConversationRead.model_validate(c) for c in conversations]


@router.post("/{conversation_id}/messages")
async def create_message(
    payload: MessageCreate, conversation: OwnedConversation, session: SessionDep
) -> MessageRead:
    """Add a message to a conversation."""
    message = await MessageRepository(session).create(
        conversation.id, MessageRole.user, payload.content
    )
    await session.commit()
    return MessageRead.model_validate(message)


@router.get("/{conversation_id}/messages")
async def list_messages(conversation: OwnedConversation, session: SessionDep) -> list[MessageRead]:
    """List a conversation's messages."""
    messages = await MessageRepository(session).list(conversation.id)
    return [MessageRead.model_validate(m) for m in messages]
