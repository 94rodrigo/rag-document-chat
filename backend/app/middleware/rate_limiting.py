from __future__ import annotations

from collections.abc import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config import get_settings
from app.infrastructure.redis import CacheService, get_pool

log = structlog.get_logger(__name__)
settings = get_settings()

_PLAN_RPM = {
    None: settings.rate_limit_anonymous_rpm,
    "free": settings.rate_limit_free_rpm,
    "pro": settings.rate_limit_pro_rpm,
    "enterprise": 1000,
}

# Endpoints that bypass the global limiter and get their own stricter bucket
_SENSITIVE_PATHS = {
    "/api/v1/auth/login": 10,       # max 10 attempts/min per IP
    "/api/v1/auth/register": 5,
    "/api/v1/auth/refresh": 20,
}

_SKIP_PATHS = {"/health", "/metrics", "/openapi.json"}


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Global rate limiter:
    - Authenticated users: plan-based RPM against a single global key (not per-path).
    - Anonymous users: IP-based RPM.
    - Sensitive auth endpoints: separate strict per-IP limit regardless of plan.
    """
    if not settings.rate_limit_enabled:
        return await call_next(request)

    if request.url.path in _SKIP_PATHS:
        return await call_next(request)

    client: Redis = Redis(connection_pool=get_pool())
    cache = CacheService(client)

    try:
        plan: str | None = None
        user_id: str | None = None
        client_ip = _get_client_ip(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.domain.auth.service import decode_access_token
                payload = decode_access_token(auth_header[7:])
                user_id = payload.get("sub")
                # NOTE: plan from JWT is used only for RPM tier selection.
                # Billing enforcement is done separately against the DB.
                plan = payload.get("plan")
            except Exception:
                pass

        # ── Sensitive endpoint: strict per-IP, ignores plan ──────────────────
        if request.url.path in _SENSITIVE_PATHS:
            ip_key = f"rl:sensitive:{_hash_ip(client_ip)}:{request.url.path}"
            limit = _SENSITIVE_PATHS[request.url.path]
            allowed, count, retry_after = await cache.check_rate_limit(ip_key, limit, 60)
            if not allowed:
                return _too_many(retry_after)

        # ── Global per-identity limiter ───────────────────────────────────────
        rpm = _PLAN_RPM.get(plan, settings.rate_limit_anonymous_rpm)
        identifier = user_id or _hash_ip(client_ip)
        # Single global key — no per-path component prevents rotation bypass
        global_key = f"rl:global:{identifier}"

        allowed, count, retry_after = await cache.check_rate_limit(global_key, rpm, 60)
        if not allowed:
            log.warning(
                "rate_limit.exceeded",
                identifier=identifier,
                path=request.url.path,
                count=count,
            )
            return _too_many(retry_after)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, rpm - count))
        return response

    finally:
        await client.aclose()


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP.

    X-Forwarded-For is only trusted when TRUSTED_PROXY_COUNT > 0, and then the IP
    is read that many hops from the right — those rightmost entries are appended by
    our own trusted proxies and cannot be forged by the client. The leftmost value
    is fully client-controlled, so trusting it (the previous behavior) let anyone
    rotate the header to evade IP-based rate limits. With no trusted proxy
    configured we ignore the header entirely and use the direct peer address.
    """
    trusted = settings.trusted_proxy_count
    if trusted > 0:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
            if parts:
                # index `trusted` from the right; clamp to the leftmost if the
                # chain is shorter than expected.
                idx = max(0, len(parts) - trusted)
                return parts[idx]
    if request.client:
        return request.client.host
    return "unknown"


def _hash_ip(ip: str) -> str:
    """One-way hash the IP for privacy-safe logging and key construction."""
    import hashlib
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _too_many(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please slow down.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
