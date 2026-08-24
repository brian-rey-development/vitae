import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.database import Base, TimestampMixin, UUIDPrimaryKey
from vitae.modules.conversations.domain.constants import CONVERSATION_TITLE_MAX_LENGTH


class ConversationModel(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(CONVERSATION_TITLE_MAX_LENGTH))
