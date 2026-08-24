from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.database import Base, TimestampMixin, UUIDPrimaryKey
from vitae.modules.users.domain.constants import EMAIL_MAX_LENGTH


class UserModel(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True, index=True)
