from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.config import get_settings
from app.domain.auth.models import Plan
from app.domain.auth.repository import AnonymousSessionRepository, UserRepository
from app.domain.billing.models import SubscriptionStatus, UsageAction
from app.domain.billing.repository import SubscriptionRepository, UsageRepository
from app.domain.billing.schemas import (
    CheckoutResponse,
    PlanLimits,
    PlanResponse,
    PortalResponse,
    SubscriptionResponse,
    UsageStatsResponse,
)
from app.domain.documents.repository import DocumentRepository
from app.shared.exceptions import (
    DocumentLimitExceededError,
    QueryLimitExceededError,
    StorageLimitExceededError,
)

log = structlog.get_logger(__name__)
settings = get_settings()


def _current_period_key() -> str:
    """YYYY-MM period key for current billing month."""
    return datetime.now(UTC).strftime("%Y-%m")


def _plan_limits(plan: str) -> tuple[int, int, int]:
    """(max_documents, max_queries_per_month, max_storage_bytes)"""
    if plan == Plan.pro:
        return (
            settings.plan_pro_documents,
            settings.plan_pro_queries_per_month,
            settings.plan_pro_storage_bytes,
        )
    if plan == Plan.enterprise:
        return (-1, -1, -1)  # unlimited
    return (
        settings.plan_free_documents,
        settings.plan_free_queries_per_month,
        settings.plan_free_storage_bytes,
    )


PLAN_CATALOG: list[dict] = [
    {
        "id": "free",
        "name": "Free",
        "price": 0.0,
        "interval": "month",
        "features": [
            "10 documents",
            "100 queries/month",
            "50 MB storage",
            "Community support",
        ],
        "limits": {"documents": 10, "queries": 100, "storage_gb": 0.05},
    },
    {
        "id": "pro",
        "name": "Pro",
        "price": 29.0,
        "interval": "month",
        "features": [
            "Unlimited documents",
            "2,000 queries/month",
            "10 GB storage",
            "Priority support",
            "API access",
        ],
        "limits": {"documents": -1, "queries": 2000, "storage_gb": 10.0},
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price": 0.0,
        "interval": "month",
        "features": [
            "Unlimited everything",
            "Custom models",
            "SSO / SAML",
            "Dedicated support",
            "SLA guarantee",
        ],
        "limits": {"documents": -1, "queries": -1, "storage_gb": -1},
    },
]


class UsageLimitService:
    """Enforces per-plan document, query, and storage limits."""

    def __init__(
        self,
        user_repo: UserRepository,
        doc_repo: DocumentRepository,
        usage_repo: UsageRepository,
        anon_repo: AnonymousSessionRepository,
    ) -> None:
        self._users = user_repo
        self._docs = doc_repo
        self._usage = usage_repo
        self._anon = anon_repo

    async def assert_can_upload(self, user_id: str, file_size: int) -> None:
        user = await self._users.get_by_id(user_id)
        if not user:
            return
        max_docs, _, max_storage = _plan_limits(user.plan)

        if max_docs != -1:
            current_count = await self._docs.count_by_user(user_id)
            if current_count >= max_docs:
                raise DocumentLimitExceededError()

        if max_storage != -1:
            current_storage = await self._docs.total_size_by_user(user_id)
            if current_storage + file_size > max_storage:
                raise StorageLimitExceededError()

    async def assert_can_query(
        self, user_id: str | None, anon_session_id: str | None
    ) -> None:
        if anon_session_id:
            # Anonymous: check in-memory counter via DB
            anon = await self._anon.get_by_hash(anon_session_id)
            if anon and anon.query_count >= settings.anon_session_max_queries:
                raise QueryLimitExceededError(
                    "Anonymous query limit reached. Sign up for more."
                )
            return

        if not user_id:
            raise QueryLimitExceededError()

        user = await self._users.get_by_id(user_id)
        if not user:
            return
        _, max_queries, _ = _plan_limits(user.plan)
        if max_queries == -1:
            return

        period = _current_period_key()
        used = await self._usage.get_count(user_id, UsageAction.query, period)
        if used >= max_queries:
            raise QueryLimitExceededError()

    async def record_query(
        self, user_id: str | None, anon_session_id: str | None
    ) -> None:
        if user_id:
            period = _current_period_key()
            await self._usage.increment(user_id, UsageAction.query, period)
        elif anon_session_id:
            # Stored in anonymous_sessions table directly
            pass

    async def get_usage_stats(self, user_id: str) -> UsageStatsResponse:
        user = await self._users.get_by_id(user_id)
        plan = user.plan if user else Plan.free
        max_docs, max_queries, max_storage = _plan_limits(plan)
        period = _current_period_key()

        docs_used = await self._docs.count_by_user(user_id)
        queries_used = await self._usage.get_count(user_id, UsageAction.query, period)
        storage_used = await self._docs.total_size_by_user(user_id)

        return UsageStatsResponse(
            documents_used=docs_used,
            documents_limit=max_docs,
            queries_used=queries_used,
            queries_limit=max_queries,
            storage_used_bytes=storage_used,
            storage_limit_bytes=max_storage,
            period_key=period,
        )


class BillingService:
    def __init__(
        self,
        sub_repo: SubscriptionRepository,
        user_repo: UserRepository,
    ) -> None:
        self._subs = sub_repo
        self._users = user_repo

    def get_plans(self) -> list[PlanResponse]:
        return [
            PlanResponse(
                id=p["id"],
                name=p["name"],
                price=p["price"],
                interval=p["interval"],
                features=p["features"],
                limits=PlanLimits(**p["limits"]),
            )
            for p in PLAN_CATALOG
        ]

    async def get_subscription(self, user_id: str) -> SubscriptionResponse | None:
        sub = await self._subs.get_by_user(user_id)
        if not sub:
            return None
        return SubscriptionResponse.model_validate(sub)

    async def create_checkout_session(
        self, user_id: str, plan_id: str, success_url: str, cancel_url: str
    ) -> CheckoutResponse:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        user = await self._users.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        price_id = {
            "pro": settings.stripe_pro_price_id,
            "enterprise": settings.stripe_enterprise_price_id,
        }.get(plan_id)

        if not price_id:
            raise ValueError(f"Unknown plan: {plan_id}")

        # Get or create Stripe customer
        sub = await self._subs.get_by_user(user_id)
        customer_id = sub.stripe_customer_id if sub else None

        if not customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name)
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id, "plan_id": plan_id},
        )
        return CheckoutResponse(url=session.url)

    async def get_portal_url(self, user_id: str, return_url: str) -> PortalResponse:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        sub = await self._subs.get_by_user(user_id)
        if not sub or not sub.stripe_customer_id:
            raise ValueError("No active subscription")

        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )
        return PortalResponse(url=session.url)

    async def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            log.warning("billing.webhook_invalid_signature")
            raise ValueError("Invalid signature")

        await self._dispatch_stripe_event(event)

    async def _dispatch_stripe_event(self, event: object) -> None:
        event_type = getattr(event, "type", "")
        data = getattr(event, "data", {})
        obj = getattr(data, "object", {}) if hasattr(data, "object") else data.get("object", {})

        handlers = {
            "checkout.session.completed": self._on_checkout_completed,
            "customer.subscription.updated": self._on_subscription_updated,
            "customer.subscription.deleted": self._on_subscription_deleted,
        }
        handler = handlers.get(event_type)
        if handler:
            await handler(obj)

    async def _on_checkout_completed(self, session: object) -> None:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        metadata = getattr(session, "metadata", {})
        user_id = metadata.get("user_id") if isinstance(metadata, dict) else None
        plan_id = metadata.get("plan_id") if isinstance(metadata, dict) else None
        stripe_sub_id = getattr(session, "subscription", None)
        customer_id = getattr(session, "customer", None)

        if not user_id or not plan_id or not stripe_sub_id:
            return

        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        sub = await self._subs.get_by_user(user_id)

        from datetime import timezone as tz
        period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=UTC
        ) if hasattr(stripe_sub, "current_period_end") else None

        if sub:
            await self._subs.update(
                sub,
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=customer_id,
                plan=plan_id,
                status=SubscriptionStatus.active,
                current_period_end=period_end,
            )
        else:
            await self._subs.create(
                user_id=user_id,
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=customer_id,
                plan=plan_id,
                status=SubscriptionStatus.active,
                current_period_end=period_end,
            )

        # Upgrade user plan
        user = await self._users.get_by_id(user_id)
        if user:
            user.plan = plan_id
        log.info("billing.subscription_activated", user_id=user_id, plan=plan_id)

    async def _on_subscription_updated(self, subscription: object) -> None:
        stripe_id = getattr(subscription, "id", None)
        if not stripe_id:
            return
        sub = await self._subs.get_by_stripe_id(stripe_id)
        if sub:
            await self._subs.update(
                sub,
                status=getattr(subscription, "status", sub.status),
                cancel_at_period_end=getattr(subscription, "cancel_at_period_end", False),
            )

    async def _on_subscription_deleted(self, subscription: object) -> None:
        stripe_id = getattr(subscription, "id", None)
        if not stripe_id:
            return
        sub = await self._subs.get_by_stripe_id(stripe_id)
        if sub:
            await self._subs.update(sub, status=SubscriptionStatus.canceled)
            user = await self._users.get_by_id(sub.user_id)
            if user:
                user.plan = Plan.free
            log.info("billing.subscription_canceled", user_id=sub.user_id)
