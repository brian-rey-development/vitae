import uuid
from dataclasses import dataclass
from datetime import date

from vitae.modules.profiles.domain.enums import Sex


@dataclass(frozen=True)
class Profile:
    user_id: uuid.UUID
    display_name: str | None
    date_of_birth: date | None
    sex: Sex | None
