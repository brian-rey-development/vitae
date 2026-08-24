import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vitae.modules.conversations.domain.constants import CONVERSATION_TITLE_MAX_LENGTH


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=CONVERSATION_TITLE_MAX_LENGTH)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
