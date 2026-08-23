import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vitae.core.db import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKey
from vitae.modules.conversations.domain.constants import CONVERSATION_TITLE_MAX_LENGTH
from vitae.modules.conversations.domain.enums import MessageRole


class ConversationModel(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(CONVERSATION_TITLE_MAX_LENGTH))

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )


class MessageModel(UUIDPrimaryKey, CreatedAtMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text())

    conversation: Mapped["ConversationModel"] = relationship(back_populates="messages")
