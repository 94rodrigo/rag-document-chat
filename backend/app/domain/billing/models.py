from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.shared.utils import generate_id, utc_now

if TYPE_CHECKING:
    from app.domain.auth.models import User


class SubscriptionStatus(StrEnum):
    active = "active"
    canceled = "canceled"
    past_due = "past_due"
    trialing = "trialing"
    incomplete = "incomplete"


class UsageAction(StrEnum):
    query = "query"
    document_upload = "document_upload"
    embedding = "embedding"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        String(20), default=SubscriptionStatus.active, nullable=False
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utc_now, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="subscription")


class UsageRecord(Base):
    """Tracks billable usage per user per billing period."""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[UsageAction] = mapped_column(String(30), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    period_key: Mapped[str] = mapped_column(
        String(7), nullable=False  # YYYY-MM
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_usage_records_user_period", "user_id", "action", "period_key"),
    )
