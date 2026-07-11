from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.documents.models import Document, DocumentChunk, DocumentStatus
from app.shared.pagination import PaginationParams
from app.shared.utils import utc_now


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> Document:
        doc = Document(**kwargs)
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_id(self, doc_id: str) -> Document | None:
        return await self._session.get(Document, doc_id)

    async def get_by_id_and_user(self, doc_id: str, user_id: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        params: PaginationParams,
        status: DocumentStatus | None = None,
    ) -> tuple[list[Document], int]:
        query = select(Document).where(Document.user_id == user_id)
        count_query = select(func.count()).select_from(Document).where(Document.user_id == user_id)

        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)

        query = (
            query
            .order_by(Document.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )

        docs_result = await self._session.execute(query)
        count_result = await self._session.execute(count_query)

        return list(docs_result.scalars().all()), count_result.scalar_one()

    async def count_by_user(self, user_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Document).where(
                Document.user_id == user_id,
                Document.status != DocumentStatus.error,
            )
        )
        return result.scalar_one()

    async def total_size_by_user(self, user_id: str) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Document.size_bytes), 0))
            .where(Document.user_id == user_id)
        )
        return result.scalar_one()

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        *,
        error_message: str | None = None,
        chunk_count: int | None = None,
        page_count: int | None = None,
        processed_at: bool = False,
    ) -> None:
        values: dict[str, Any] = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if chunk_count is not None:
            values["chunk_count"] = chunk_count
        if page_count is not None:
            values["page_count"] = page_count
        if processed_at:
            values["processed_at"] = utc_now()

        await self._session.execute(
            update(Document).where(Document.id == doc_id).values(**values)
        )

    async def delete(self, doc: Document) -> None:
        await self._session.delete(doc)
        await self._session.flush()


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, chunks: list[DocumentChunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def get_by_document(self, document_id: str) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def similarity_search(
        self,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        top_k: int = 6,
        similarity_threshold: float = 0.35,
    ) -> list[tuple[DocumentChunk, float]]:
        """Cosine similarity search against pgvector index."""
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import cast, literal

        embedding_literal = cast(
            literal(str(query_embedding).replace(" ", "")),
            Vector(len(query_embedding))
        )
        distance_expr = DocumentChunk.embedding.cosine_distance(embedding_literal)

        result = await self._session.execute(
            select(DocumentChunk, (1 - distance_expr).label("similarity"))
            .where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.document_id.in_(document_ids),
                (1 - distance_expr) >= similarity_threshold,
            )
            .order_by(distance_expr)
            .limit(top_k)
        )
        return [(row[0], float(row[1])) for row in result.all()]

    async def delete_by_document(self, document_id: str) -> None:
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for chunk in result.scalars().all():
            await self._session.delete(chunk)
        await self._session.flush()
