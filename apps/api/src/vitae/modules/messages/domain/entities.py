import uuid
from dataclasses import dataclass
from datetime import datetime

from vitae.modules.messages.domain.enums import MessageRole


@dataclass(frozen=True)
class Message:
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
