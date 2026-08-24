import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.database import Base, TimestampMixin
from vitae.modules.profiles.domain.constants import DISPLAY_NAME_MAX_LENGTH
from vitae.modules.profiles.domain.enums import Sex


class ProfileModel(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    date_of_birth: Mapped[date | None] = mapped_column(Date())
    sex: Mapped[Sex | None] = mapped_column(SAEnum(Sex, name="sex"))
