from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.infrastructure.database import Base
from app.shared.utils import generate_id, utc_now

if TYPE_CHECKING:
    from app.domain.auth.models import User
    from app.domain.conversations.models import Citation

settings = get_settings()


class DocumentStatus(StrEnum):
    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    error = "error"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        String(20), default=DocumentStatus.uploading, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship("User", back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "status"),
        Index("ix_documents_created_at", "created_at"),
    )


class DocumentChunk(Base):
    """A text chunk from a processed document with its embedding vector."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # denormalized for fast filtering
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(
        Vector(settings.rag_embedding_dimensions), nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
    citations: Mapped[list[Citation]] = relationship(
        "Citation", back_populates="chunk"
    )

    __table_args__ = (
        Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"),
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
