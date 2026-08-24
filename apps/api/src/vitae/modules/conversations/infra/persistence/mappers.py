from vitae.modules.conversations.domain.entities import Conversation
from vitae.modules.conversations.infra.persistence.models import ConversationModel


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
