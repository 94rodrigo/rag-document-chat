from __future__ import annotations

import asyncio
from typing import Any

import structlog
from celery import Task

from app.workers.celery_app import celery

log = structlog.get_logger(__name__)


class DocumentProcessingTask(Task):
    abstract = True

    def on_failure(
        self, exc: Exception, task_id: str, args: list, kwargs: dict, einfo: Any
    ) -> None:
        log.error(
            "task.document_processing_failed",
            task_id=task_id,
            doc_id=args[0] if args else None,
            error=str(exc),
        )


@celery.task(
    bind=True,
    base=DocumentProcessingTask,
    name="app.workers.tasks.document_processing.process_document",
    queue="documents",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def process_document(self: Task, document_id: str) -> dict[str, Any]:
    """
    Full document processing pipeline:
    1. Download from object storage
    2. Parse (PDF / DOCX / DOC / EPUB / text)
    3. Chunk (recursive / semantic / hybrid)
    4. Embed (OpenAI / VoyageAI / BGE)
    5. Store vectors (pgvector / Qdrant)
    6. Update document status → ready
    """
    return asyncio.run(_process_document_async(document_id))


async def _process_document_async(document_id: str) -> dict[str, Any]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    # Import all models so SQLAlchemy can resolve cross-model relationships
    import app.domain.auth.models  # noqa: F401
    import app.domain.billing.models  # noqa: F401
    import app.domain.conversations.models  # noqa: F401
    import app.domain.documents.models  # noqa: F401
    from app.config import get_settings
    from app.domain.documents.models import DocumentStatus
    from app.domain.documents.repository import DocumentRepository
    from app.domain.rag.parsers.registry import parse_document
    from app.domain.rag.pipeline import build_pipeline
    from app.infrastructure.storage import get_storage

    log.info("task.process_document.start", doc_id=document_id)

    # NullPool avoids reusing connections across event loops — asyncio.run()
    # creates a fresh loop per task invocation, which invalidates pooled
    # asyncpg connections established in a previous loop.
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)

    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as session:
            doc_repo = DocumentRepository(session)
            storage = get_storage()

            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                log.error("task.document_not_found", doc_id=document_id)
                return {"status": "error", "reason": "document not found"}

            try:
                log.info("task.process_document.downloading", doc_id=document_id)
                content = await storage.download(doc.s3_key)

                log.info("task.process_document.parsing", doc_id=document_id, mime=doc.mime_type)
                parsed = parse_document(content, doc.mime_type)

                pipeline = build_pipeline(session)

                log.info(
                    "task.process_document.indexing",
                    doc_id=document_id,
                    pages=parsed.total_pages,
                )
                text_chunks = await pipeline.index_document(
                    parsed=parsed,
                    document_id=document_id,
                    user_id=doc.user_id,
                )

                if not text_chunks:
                    await doc_repo.update_status(
                        document_id,
                        DocumentStatus.error,
                        error_message="No text could be extracted from the document",
                    )
                    await session.commit()
                    return {"status": "error", "reason": "empty document"}

                await doc_repo.update_status(
                    document_id,
                    DocumentStatus.ready,
                    chunk_count=len(text_chunks),
                    page_count=parsed.total_pages,
                    processed_at=True,
                )
                await session.commit()

                log.info(
                    "task.process_document.complete",
                    doc_id=document_id,
                    chunks=len(text_chunks),
                    pages=parsed.total_pages,
                )
                return {
                    "status": "ready",
                    "document_id": document_id,
                    "chunk_count": len(text_chunks),
                    "page_count": parsed.total_pages,
                }

            except Exception as e:
                log.exception("task.process_document.error", doc_id=document_id)
                await doc_repo.update_status(
                    document_id,
                    DocumentStatus.error,
                    error_message=str(e)[:1000],
                )
                await session.commit()
                raise
    finally:
        await engine.dispose()
