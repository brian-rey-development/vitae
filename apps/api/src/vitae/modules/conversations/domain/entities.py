import uuid
from dataclasses import dataclass
from datetime import datetime

from vitae.modules.conversations.domain.enums import MessageRole


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    created_at: datetime


@dataclass(frozen=True)
class Message:
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
