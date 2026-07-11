from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import cast, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.models import DocumentChunk
from app.domain.rag.stores.base import VectorSearchResult

log = structlog.get_logger(__name__)


class PgVectorStore:
    """
    Vector store backed by PostgreSQL + pgvector.
    Uses cosine similarity with the IVFFlat index on DocumentChunk.embedding.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        document_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        records = [
            DocumentChunk(
                id=c["id"],
                document_id=document_id,
                user_id=user_id,
                content=c["content"],
                embedding=c["embedding"],
                page_number=c.get("page_number"),
                chunk_index=c["chunk_index"],
                token_count=c["token_count"],
                chunk_metadata=c.get("metadata", {}),
            )
            for c in chunks
        ]
        self._session.add_all(records)
        await self._session.flush()
        log.debug("store.pgvector.upserted", count=len(records), document_id=document_id)

    async def search(
        self,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        top_k: int,
        similarity_threshold: float = 0.35,
    ) -> list[VectorSearchResult]:
        # Hard assertion: an empty document_ids list would return chunks from ANY
        # document, causing cross-tenant data leakage.
        if not document_ids:
            log.error("store.pgvector.empty_document_ids_rejected", user_id=user_id)
            return []
        if not user_id:
            log.error("store.pgvector.empty_user_id_rejected")
            return []
        from pgvector.sqlalchemy import Vector

        embedding_literal = cast(
            literal(str(query_embedding).replace(" ", "")),
            Vector(len(query_embedding)),
        )
        distance_expr = DocumentChunk.embedding.cosine_distance(embedding_literal)
        similarity_expr = (1 - distance_expr).label("similarity")

        result = await self._session.execute(
            select(DocumentChunk, similarity_expr)
            .where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.document_id.in_(document_ids),
                (1 - distance_expr) >= similarity_threshold,
            )
            .order_by(distance_expr)
            .limit(top_k)
        )

        rows = result.all()
        return [
            VectorSearchResult(
                chunk_id=row[0].id,
                document_id=row[0].document_id,
                content=row[0].content,
                page_number=row[0].page_number,
                chunk_index=row[0].chunk_index,
                score=float(row[1]),
                metadata=row[0].chunk_metadata or {},
            )
            for row in rows
        ]

    async def delete(self, document_id: str) -> None:
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for chunk in result.scalars().all():
            await self._session.delete(chunk)
        await self._session.flush()
