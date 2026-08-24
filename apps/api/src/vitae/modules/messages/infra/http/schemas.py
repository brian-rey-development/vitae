import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vitae.modules.messages.domain.constants import MESSAGE_CONTENT_MAX_LENGTH
from vitae.modules.messages.domain.enums import MessageRole


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MESSAGE_CONTENT_MAX_LENGTH)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
