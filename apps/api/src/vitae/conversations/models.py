import uuid
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vitae.core.db import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKey

CONVERSATION_TITLE_MAX_LENGTH = 200
MESSAGE_CONTENT_MAX_LENGTH = 8000


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class Conversation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(CONVERSATION_TITLE_MAX_LENGTH))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(UUIDPrimaryKey, CreatedAtMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
