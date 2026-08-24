from vitae.modules.messages.domain.entities import Message
from vitae.modules.messages.infra.persistence.models import MessageModel


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
