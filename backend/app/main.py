from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.infrastructure.database import check_db_health, enable_pgvector
from app.infrastructure.redis import check_redis_health
from app.infrastructure.storage import get_storage
from app.middleware.logging import RequestLoggingMiddleware, configure_logging
from app.middleware.rate_limiting import rate_limit_middleware
from app.shared.exceptions import AppError

log = structlog.get_logger(__name__)
settings = get_settings()

configure_logging()


# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds defensive HTTP security headers to every response."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app.starting", env=settings.app_env)

    await enable_pgvector()

    try:
        await get_storage().ensure_bucket()
    except Exception:
        log.warning("app.storage_init_failed")

    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1,
        )

    log.info("app.started")
    yield
    log.info("app.stopped")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Docna API",
        description="Document Q&A SaaS — RAG backend",
        version="0.1.0",
        # Never expose API docs in production
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware (order: outermost first) ────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Anon-Session"],
        expose_headers=["X-Request-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.middleware("http")(rate_limit_middleware)

    # ── Exception handlers ────────────────────────────────────────────────

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

    # ── Prometheus metrics (internal only) ────────────────────────────────

    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health"],
        ).instrument(app)

        # Expose /metrics only on an internal port or with token auth, never publicly
        metrics_token = settings.metrics_auth_token
        if metrics_token:
            @app.get("/metrics", include_in_schema=False)
            async def metrics_endpoint(request: Request):
                auth = request.headers.get("Authorization", "")
                if auth != f"Bearer {metrics_token}":
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                # Delegate to Instrumentator's internal endpoint
                from fastapi.responses import Response as _Resp
                from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
                return _Resp(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        else:
            # If no token configured: expose only in development
            if settings.is_development:
                instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
            else:
                log.warning(
                    "app.metrics_disabled",
                    reason="METRICS_AUTH_TOKEN not set in production",
                )

    except ImportError:
        pass

    # ── Routes ────────────────────────────────────────────────────────────

    app.include_router(api_router)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, Any]:
        db_ok = await check_db_health()
        redis_ok = await check_redis_health()
        healthy = db_ok and redis_ok
        # Don't reveal which subsystem is failing in production
        if settings.is_production:
            return {"status": "healthy" if healthy else "degraded"}
        return {
            "status": "healthy" if healthy else "degraded",
            "db": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
            "version": "0.1.0",
        }

    return app


app = create_app()
