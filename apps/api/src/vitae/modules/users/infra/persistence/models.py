import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vitae.core.database import Base, TimestampMixin, UUIDPrimaryKey
from vitae.modules.users.domain.constants import DISPLAY_NAME_MAX_LENGTH, EMAIL_MAX_LENGTH
from vitae.modules.users.domain.enums import Sex


class UserModel(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True, index=True)

    profile: Mapped["ProfileModel | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class ProfileModel(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    date_of_birth: Mapped[date | None] = mapped_column(Date())
    sex: Mapped[Sex | None] = mapped_column(SAEnum(Sex, name="sex"))

    user: Mapped["UserModel"] = relationship(back_populates="profile")
