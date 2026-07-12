from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.models import Subscription, UsageAction, UsageRecord


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> Subscription:
        sub = Subscription(**kwargs)
        self._session.add(sub)
        await self._session.flush()
        return sub

    async def get_by_user(self, user_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_id(self, stripe_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, sub: Subscription, **kwargs: Any) -> Subscription:
        for key, value in kwargs.items():
            setattr(sub, key, value)
        await self._session.flush()
        return sub


class UsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment(
        self,
        user_id: str,
        action: UsageAction,
        period_key: str,
        count: int = 1,
    ) -> int:
        """Upsert usage record and return new total."""
        result = await self._session.execute(
            select(UsageRecord).where(
                UsageRecord.user_id == user_id,
                UsageRecord.action == action,
                UsageRecord.period_key == period_key,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.count += count
            await self._session.flush()
            return record.count
        else:
            new_record = UsageRecord(
                user_id=user_id,
                action=action,
                period_key=period_key,
                count=count,
            )
            self._session.add(new_record)
            await self._session.flush()
            return count

    async def get_count(
        self,
        user_id: str,
        action: UsageAction,
        period_key: str,
    ) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(UsageRecord.count), 0))
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.action == action,
                UsageRecord.period_key == period_key,
            )
        )
        return result.scalar_one()
