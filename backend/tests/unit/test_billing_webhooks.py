from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import stripe

from app.domain.auth.models import Plan
from app.domain.billing.models import SubscriptionStatus
from app.domain.billing.service import BillingService
from tests.conftest import (
    FakeSubscription,
    FakeSubscriptionRepository,
    FakeUser,
    FakeUserRepository,
)

PERIOD_END_TS = 1_767_225_600  # 2026-01-01T00:00:00Z


def make_event(event_type: str, obj: object) -> SimpleNamespace:
    """Mirrors the shape of a stripe.Event: event.type and event.data.object."""
    return SimpleNamespace(type=event_type, data=SimpleNamespace(object=obj))


def checkout_session(
    user_id: str | None = "user-1",
    plan_id: str | None = "pro",
    subscription: str | None = "sub_123",
    customer: str | None = "cus_123",
) -> SimpleNamespace:
    metadata = {}
    if user_id is not None:
        metadata["user_id"] = user_id
    if plan_id is not None:
        metadata["plan_id"] = plan_id
    return SimpleNamespace(
        metadata=metadata, subscription=subscription, customer=customer
    )


@pytest.fixture
def stub_stripe_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    """stripe.Subscription.retrieve is a network call; return a fixed object instead."""
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        lambda *args, **kwargs: SimpleNamespace(current_period_end=PERIOD_END_TS),
    )


def build_service(
    user: FakeUser | None = None, subs: list[FakeSubscription] | None = None
) -> tuple[BillingService, FakeSubscriptionRepository, FakeUserRepository]:
    sub_repo = FakeSubscriptionRepository(subs)
    user_repo = FakeUserRepository([user] if user else [])
    return BillingService(sub_repo=sub_repo, user_repo=user_repo), sub_repo, user_repo


class TestCheckoutCompleted:
    async def test_creates_subscription_and_upgrades_the_user(
        self, free_user, stub_stripe_subscription
    ) -> None:
        svc, sub_repo, _ = build_service(user=free_user)
        event = make_event("checkout.session.completed", checkout_session())

        await svc._dispatch_stripe_event(event)

        assert len(sub_repo.created) == 1
        sub = sub_repo.created[0]
        assert sub.user_id == "user-1"
        assert sub.plan == "pro"
        assert sub.stripe_subscription_id == "sub_123"
        assert sub.stripe_customer_id == "cus_123"
        assert sub.status == SubscriptionStatus.active
        assert free_user.plan == "pro"

    async def test_sets_current_period_end_from_stripe(
        self, free_user, stub_stripe_subscription
    ) -> None:
        svc, sub_repo, _ = build_service(user=free_user)

        await svc._dispatch_stripe_event(
            make_event("checkout.session.completed", checkout_session())
        )

        assert sub_repo.created[0].current_period_end == datetime.fromtimestamp(
            PERIOD_END_TS, tz=UTC
        )

    async def test_updates_an_existing_subscription_instead_of_duplicating(
        self, free_user, stub_stripe_subscription
    ) -> None:
        existing = FakeSubscription(user_id="user-1", plan=Plan.free)
        svc, sub_repo, _ = build_service(user=free_user, subs=[existing])

        await svc._dispatch_stripe_event(
            make_event("checkout.session.completed", checkout_session())
        )

        assert sub_repo.created == []
        assert len(sub_repo.subs) == 1
        assert existing.plan == "pro"
        assert existing.status == SubscriptionStatus.active
        assert existing.stripe_subscription_id == "sub_123"

    @pytest.mark.parametrize(
        "session",
        [
            checkout_session(user_id=None),
            checkout_session(plan_id=None),
            checkout_session(subscription=None),
        ],
        ids=["missing_user_id", "missing_plan_id", "missing_subscription"],
    )
    async def test_incomplete_session_is_ignored(
        self, free_user, stub_stripe_subscription, session
    ) -> None:
        """A malformed event must not create a subscription or change the plan."""
        svc, sub_repo, _ = build_service(user=free_user)

        await svc._dispatch_stripe_event(
            make_event("checkout.session.completed", session)
        )

        assert sub_repo.created == []
        assert free_user.plan == Plan.free


class TestSubscriptionUpdated:
    async def test_status_and_cancellation_flag_are_synced(self, free_user) -> None:
        existing = FakeSubscription(
            user_id="user-1", stripe_subscription_id="sub_123", plan="pro"
        )
        svc, _, _ = build_service(user=free_user, subs=[existing])
        event = make_event(
            "customer.subscription.updated",
            SimpleNamespace(
                id="sub_123",
                status=SubscriptionStatus.past_due,
                cancel_at_period_end=True,
            ),
        )

        await svc._dispatch_stripe_event(event)

        assert existing.status == SubscriptionStatus.past_due
        assert existing.cancel_at_period_end is True

    async def test_event_for_unknown_subscription_is_ignored(self, free_user) -> None:
        existing = FakeSubscription(
            user_id="user-1", stripe_subscription_id="sub_123", plan="pro"
        )
        svc, _, _ = build_service(user=free_user, subs=[existing])
        event = make_event(
            "customer.subscription.updated",
            SimpleNamespace(id="sub_OTHER", status=SubscriptionStatus.canceled),
        )

        await svc._dispatch_stripe_event(event)

        assert existing.status == SubscriptionStatus.active


class TestSubscriptionDeleted:
    async def test_cancels_subscription_and_downgrades_user_to_free(
        self, pro_user
    ) -> None:
        existing = FakeSubscription(
            user_id="user-1", stripe_subscription_id="sub_123", plan="pro"
        )
        svc, _, _ = build_service(user=pro_user, subs=[existing])
        event = make_event(
            "customer.subscription.deleted", SimpleNamespace(id="sub_123")
        )

        await svc._dispatch_stripe_event(event)

        assert existing.status == SubscriptionStatus.canceled
        assert pro_user.plan == Plan.free

    async def test_deletion_of_unknown_subscription_leaves_user_untouched(
        self, pro_user
    ) -> None:
        svc, _, _ = build_service(user=pro_user, subs=[])
        event = make_event(
            "customer.subscription.deleted", SimpleNamespace(id="sub_ghost")
        )

        await svc._dispatch_stripe_event(event)

        assert pro_user.plan == Plan.pro


class TestEventDispatch:
    async def test_unhandled_event_type_is_a_no_op(self, free_user) -> None:
        svc, sub_repo, _ = build_service(user=free_user)
        event = make_event("invoice.payment_failed", SimpleNamespace(id="in_123"))

        await svc._dispatch_stripe_event(event)

        assert sub_repo.created == []
        assert free_user.plan == Plan.free

    async def test_event_without_a_type_is_a_no_op(self, free_user) -> None:
        svc, sub_repo, _ = build_service(user=free_user)

        await svc._dispatch_stripe_event(SimpleNamespace(data=SimpleNamespace(object={})))

        assert sub_repo.created == []


class TestWebhookSignature:
    async def test_invalid_signature_is_rejected(
        self, free_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unverified payload must never reach the handlers."""
        svc, sub_repo, _ = build_service(user=free_user)

        def raise_sig_error(*args, **kwargs):
            raise stripe.error.SignatureVerificationError(
                "Invalid signature", "bad-sig-header"
            )

        monkeypatch.setattr(stripe.Webhook, "construct_event", raise_sig_error)

        with pytest.raises(ValueError, match="Invalid signature"):
            await svc.handle_webhook(b'{"type": "checkout.session.completed"}', "bad-sig")

        assert sub_repo.created == []
        assert free_user.plan == Plan.free

    async def test_verified_payload_is_dispatched(
        self, free_user, stub_stripe_subscription, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svc, sub_repo, _ = build_service(user=free_user)
        event = make_event("checkout.session.completed", checkout_session())
        monkeypatch.setattr(
            stripe.Webhook, "construct_event", lambda *args, **kwargs: event
        )

        await svc.handle_webhook(b"{}", "good-sig")

        assert len(sub_repo.created) == 1
        assert free_user.plan == "pro"
