import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    created_at: datetime
