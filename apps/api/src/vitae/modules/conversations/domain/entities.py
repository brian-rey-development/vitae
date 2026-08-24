import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    created_at: datetime
