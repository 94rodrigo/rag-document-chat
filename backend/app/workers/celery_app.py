from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging, worker_ready

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "citenest",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.document_processing",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,            # ack only after completion
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,   # process one task at a time per worker
    task_routes={
        "app.workers.tasks.document_processing.*": {"queue": "documents"},
    },
    task_soft_time_limit=300,   # 5 min soft limit
    task_time_limit=600,        # 10 min hard limit
    result_expires=86400,       # keep results for 1 day
)


@setup_logging.connect
def setup_celery_logging(**kwargs: object) -> None:
    from app.middleware.logging import configure_logging
    configure_logging()


@worker_ready.connect
def on_worker_ready(**kwargs: object) -> None:
    import structlog
    log = structlog.get_logger(__name__)
    log.info("celery.worker_ready")
