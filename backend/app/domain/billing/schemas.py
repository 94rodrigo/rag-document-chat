from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    interval: str
    features: list[str]
    limits: PlanLimits


class PlanLimits(BaseModel):
    documents: int
    queries: int
    storage_gb: float


class SubscriptionResponse(BaseModel):
    id: str
    plan: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool

    model_config = {"from_attributes": True}


class UsageStatsResponse(BaseModel):
    documents_used: int
    documents_limit: int
    queries_used: int
    queries_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
    period_key: str


class CheckoutRequest(BaseModel):
    plan_id: str


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str
