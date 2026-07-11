from __future__ import annotations

import structlog

from app.domain.rag.retrievers.base import RetrievedChunk
from app.domain.rag.stores.base import VectorStoreProtocol

log = structlog.get_logger(__name__)


class DenseRetriever:
    """ANN cosine similarity search via the configured vector store."""

    def __init__(self, store: VectorStoreProtocol) -> None:
        self._store = store

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
        results = await self._store.search(
            query_embedding=query_embedding,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        chunks = [
            RetrievedChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_name=document_names.get(r.document_id, "Unknown"),
                content=r.content,
                page_number=r.page_number,
                chunk_index=r.chunk_index,
                score=r.score,
                retrieval_method="dense",
                metadata=r.metadata,
            )
            for r in results
        ]

        log.debug(
            "retriever.dense.done",
            count=len(chunks),
            top_score=chunks[0].score if chunks else 0,
        )
        return chunks
