from vitae.modules.conversations.domain.entities import Conversation, Message
from vitae.modules.conversations.infra.persistence.models import ConversationModel, MessageModel


def to_conversation(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        created_at=model.created_at,
    )


def to_conversation_model(entity: Conversation) -> ConversationModel:
    return ConversationModel(
        id=entity.id,
        user_id=entity.user_id,
        title=entity.title,
        created_at=entity.created_at,
    )


def to_message(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        role=model.role,
        content=model.content,
        created_at=model.created_at,
    )


def to_message_model(entity: Message) -> MessageModel:
    return MessageModel(
        id=entity.id,
        conversation_id=entity.conversation_id,
        role=entity.role,
        content=entity.content,
        created_at=entity.created_at,
    )
