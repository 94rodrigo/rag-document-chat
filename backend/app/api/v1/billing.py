from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.dependencies import CurrentUser, get_billing_service, get_usage_limit_service
from app.domain.billing.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    PortalResponse,
    SubscriptionResponse,
    UsageStatsResponse,
)
from app.domain.billing.service import BillingService, UsageLimitService

router = APIRouter(prefix="/billing", tags=["billing"])

BillSvc = Annotated[BillingService, Depends(get_billing_service)]
UsageSvc = Annotated[UsageLimitService, Depends(get_usage_limit_service)]


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans(svc: BillSvc) -> list[PlanResponse]:
    return svc.get_plans()


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    current_user: CurrentUser, svc: BillSvc
) -> SubscriptionResponse | None:
    return await svc.get_subscription(current_user.id)


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage(current_user: CurrentUser, svc: UsageSvc) -> UsageStatsResponse:
    return await svc.get_usage_stats(current_user.id)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    current_user: CurrentUser,
    svc: BillSvc,
) -> CheckoutResponse:
    base = str(request.base_url).rstrip("/")
    return await svc.create_checkout_session(
        user_id=current_user.id,
        plan_id=body.plan_id,
        success_url=f"{base}/billing?success=1",
        cancel_url=f"{base}/billing?canceled=1",
    )


@router.post("/portal", response_model=PortalResponse)
async def get_portal(
    request: Request, current_user: CurrentUser, svc: BillSvc
) -> PortalResponse:
    base = str(request.base_url).rstrip("/")
    return await svc.get_portal_url(current_user.id, return_url=f"{base}/billing")


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def stripe_webhook(
    request: Request,
    svc: BillSvc,
    stripe_signature: Annotated[str | None, Header()] = None,
) -> None:
    payload = await request.body()
    if stripe_signature:
        await svc.handle_webhook(payload, stripe_signature)
