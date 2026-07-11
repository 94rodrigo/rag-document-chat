from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag.retrievers.base import RetrievedChunk

log = structlog.get_logger(__name__)

_BM25_SQL = text(
    """
    SELECT
        dc.id               AS chunk_id,
        dc.document_id,
        dc.content,
        dc.page_number,
        dc.chunk_index,
        dc.chunk_metadata,
        ts_rank_cd(
            to_tsvector('english', dc.content),
            plainto_tsquery('english', :query),
            32
        )                   AS bm25_score
    FROM document_chunks dc
    WHERE
        dc.user_id   = :user_id
        AND dc.document_id = ANY(:document_ids)
        AND to_tsvector('english', dc.content)
            @@ plainto_tsquery('english', :query)
    ORDER BY bm25_score DESC
    LIMIT :top_k
    """
)


class BM25Retriever:
    """
    Keyword retrieval via PostgreSQL full-text search (ts_rank_cd / BM25).
    No schema changes required; to_tsvector is computed on-the-fly.

    For large corpora, add a GIN index:
        CREATE INDEX CONCURRENTLY ix_chunks_fts
        ON document_chunks USING gin(to_tsvector('english', content));
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        document_names: dict[str, str],
        top_k: int,
        similarity_threshold: float,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []

        result = await self._session.execute(
            _BM25_SQL,
            {
                "query": query,
                "user_id": user_id,
                "document_ids": document_ids,
                "top_k": top_k,
            },
        )

        rows = result.mappings().all()
        chunks = [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_name=document_names.get(row["document_id"], "Unknown"),
                content=row["content"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                score=float(row["bm25_score"]),
                retrieval_method="bm25",
                metadata=row["chunk_metadata"] or {},
            )
            for row in rows
        ]

        log.debug("retriever.bm25.done", count=len(chunks))
        return chunks
