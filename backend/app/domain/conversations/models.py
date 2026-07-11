from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.shared.utils import generate_id, utc_now

if TYPE_CHECKING:
    from app.domain.auth.models import User
    from app.domain.documents.models import DocumentChunk


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    anon_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), default="New conversation", nullable=False)
    document_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )

    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    msg_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
    citations: Mapped[list[Citation]] = relationship(
        "Citation", back_populates="message", cascade="all, delete-orphan"
    )


class Citation(Base):
    """Links an assistant message to a retrieved document chunk."""

    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    citation_index: Mapped[int] = mapped_column(Integer, nullable=False)

    message: Mapped[Message] = relationship("Message", back_populates="citations")
    chunk: Mapped[DocumentChunk | None] = relationship("DocumentChunk", back_populates="citations")
