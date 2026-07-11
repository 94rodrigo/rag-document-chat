from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.shared.utils import generate_id, utc_now

if TYPE_CHECKING:
    from app.domain.billing.models import Subscription
    from app.domain.documents.models import Document


class Plan(StrEnum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plan: Mapped[Plan] = mapped_column(String(20), default=Plan.free, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    notify_document_processing: Mapped[bool] = mapped_column(default=True, nullable=False)
    notify_weekly_summary: Mapped[bool] = mapped_column(default=False, nullable=False)
    notify_product_updates: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )

    # relationships
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Subscription | None] = relationship(
        "Subscription", back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_token_hash", "token_hash"),)

    @property
    def is_valid(self) -> bool:
        from app.shared.utils import utc_now as _now
        return self.revoked_at is None and self.expires_at > _now()


class AnonymousSession(Base):
    """Tracks anonymous (unauthenticated) usage sessions."""

    __tablename__ = "anonymous_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    session_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    query_count: Mapped[int] = mapped_column(default=0, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
