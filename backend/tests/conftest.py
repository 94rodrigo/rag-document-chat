from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.domain.auth.models import Plan
from app.domain.billing.models import SubscriptionStatus
from app.domain.rag.retrievers.base import RetrievedChunk

# In-memory doubles for the repository layer. They implement the same surface the
# services actually call, so the service logic under test runs for real — only the
# database is replaced.


@dataclass
class FakeUser:
    id: str = "user-1"
    email: str = "user@example.com"
    name: str = "Test User"
    plan: str = Plan.free


@dataclass
class FakeAnonSession:
    query_count: int = 0


@dataclass
class FakeSubscription:
    user_id: str = "user-1"
    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    plan: str = Plan.free
    status: str = SubscriptionStatus.active
    current_period_end: Any = None
    cancel_at_period_end: bool = False


class FakeUserRepository:
    def __init__(self, users: list[FakeUser] | None = None) -> None:
        self.users = {u.id: u for u in (users or [])}

    async def get_by_id(self, user_id: str) -> FakeUser | None:
        return self.users.get(user_id)


class FakeDocumentRepository:
    def __init__(self, count: int = 0, total_size: int = 0) -> None:
        self._count = count
        self._total_size = total_size

    async def count_by_user(self, user_id: str) -> int:
        return self._count

    async def total_size_by_user(self, user_id: str) -> int:
        return self._total_size


class FakeUsageRepository:
    def __init__(self, counts: dict[tuple[str, str, str], int] | None = None) -> None:
        self.counts: dict[tuple[str, str, str], int] = counts or {}
        self.increments: list[tuple[str, str, str]] = []

    async def get_count(self, user_id: str, action: str, period: str) -> int:
        return self.counts.get((user_id, str(action), period), 0)

    async def increment(self, user_id: str, action: str, period: str) -> None:
        key = (user_id, str(action), period)
        self.counts[key] = self.counts.get(key, 0) + 1
        self.increments.append(key)


class FakeAnonRepository:
    def __init__(self, sessions: dict[str, FakeAnonSession] | None = None) -> None:
        self.sessions = sessions or {}

    async def get_by_hash(self, token_hash: str) -> FakeAnonSession | None:
        return self.sessions.get(token_hash)


class FakeSubscriptionRepository:
    def __init__(self, subs: list[FakeSubscription] | None = None) -> None:
        self.subs: list[FakeSubscription] = list(subs or [])
        self.created: list[FakeSubscription] = []

    async def get_by_user(self, user_id: str) -> FakeSubscription | None:
        return next((s for s in self.subs if s.user_id == user_id), None)

    async def get_by_stripe_id(self, stripe_id: str) -> FakeSubscription | None:
        return next(
            (s for s in self.subs if s.stripe_subscription_id == stripe_id), None
        )

    async def create(self, **kwargs: Any) -> FakeSubscription:
        sub = FakeSubscription(**kwargs)
        self.subs.append(sub)
        self.created.append(sub)
        return sub

    async def update(self, sub: FakeSubscription, **kwargs: Any) -> FakeSubscription:
        for key, value in kwargs.items():
            setattr(sub, key, value)
        return sub


@pytest.fixture
def free_user() -> FakeUser:
    return FakeUser(id="user-1", plan=Plan.free)


@pytest.fixture
def pro_user() -> FakeUser:
    return FakeUser(id="user-1", plan=Plan.pro)


@pytest.fixture
def enterprise_user() -> FakeUser:
    return FakeUser(id="user-1", plan=Plan.enterprise)


def make_chunk(chunk_id: str, score: float = 0.0, content: str = "") -> RetrievedChunk:
    """A RetrievedChunk with only the fields the fusion logic cares about varying."""
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        document_name="doc.pdf",
        content=content or f"content of {chunk_id}",
        page_number=1,
        chunk_index=0,
        score=score,
        retrieval_method="dense",
    )
