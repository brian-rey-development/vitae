import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vitae.core.db import Base, TimestampMixin, UUIDPrimaryKey

DISPLAY_NAME_MAX_LENGTH = 120


class Sex(StrEnum):
    male = "male"
    female = "female"
    other = "other"
    undisclosed = "undisclosed"


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    date_of_birth: Mapped[date | None] = mapped_column(Date())
    sex: Mapped[Sex | None] = mapped_column(SAEnum(Sex, name="sex"))

    user: Mapped["User"] = relationship(back_populates="profile")
