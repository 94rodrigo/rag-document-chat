from __future__ import annotations

import logging
import re
import sys
import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request
from structlog.typing import EventDict

from app.config import LogFormat, get_settings

settings = get_settings()

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _safe_log(value: str, max_len: int = 500) -> str:
    """Strip control characters (prevents log injection) and truncate."""
    return _CONTROL_CHARS.sub("", value)[:max_len]


def _add_request_id(
    logger: object, method: str, event_dict: EventDict
) -> EventDict:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the application."""
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_request_id,
    ]

    if settings.log_format == LogFormat.json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to go through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


class RequestLoggingMiddleware:
    """Structured request/response logging with timing."""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(
        self, scope: dict, receive: Callable, send: Callable
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        log = structlog.get_logger(__name__)
        start = time.perf_counter()

        status_code = 500
        response_started = False

        async def send_with_logging(message: dict) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode())
                ]
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            level = "warning" if status_code >= 400 else "info"
            getattr(log, level)(
                "http.request",
                method=request.method,
                # Sanitise user-controlled values to prevent log injection
                path=_safe_log(request.url.path),
                status=status_code,
                duration_ms=duration_ms,
                user_agent=_safe_log(request.headers.get("user-agent", ""), max_len=200),
            )
