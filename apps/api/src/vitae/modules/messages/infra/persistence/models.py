import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from vitae.core.database import Base, CreatedAtMixin, UUIDPrimaryKey
from vitae.modules.messages.domain.enums import MessageRole


class MessageModel(UUIDPrimaryKey, CreatedAtMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text())
