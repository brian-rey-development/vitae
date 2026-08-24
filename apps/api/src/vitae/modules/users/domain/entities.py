import uuid
from dataclasses import dataclass
from datetime import date, datetime

from vitae.modules.users.domain.enums import Sex


@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    created_at: datetime


@dataclass(frozen=True)
class Profile:
    user_id: uuid.UUID
    display_name: str | None
    date_of_birth: date | None
    sex: Sex | None
