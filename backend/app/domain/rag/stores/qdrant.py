from __future__ import annotations

from typing import Any
from uuid import uuid5, NAMESPACE_DNS

import structlog

from app.domain.rag.stores.base import VectorSearchResult

log = structlog.get_logger(__name__)

_PAYLOAD_FIELDS = ("document_id", "user_id", "content", "page_number", "chunk_index", "metadata")


def _str_to_uint64(s: str) -> int:
    """Convert a string ID to a stable uint64 for Qdrant point IDs."""
    return uuid5(NAMESPACE_DNS, s).int >> 64


class QdrantStore:
    """
    Vector store backed by Qdrant. Each chunk is stored as a point in a
    single shared collection, filtered by user_id and document_id at query time.
    """

    def __init__(
        self,
        url: str,
        collection: str,
        api_key: str = "",
        embedding_dimensions: int = 1536,
    ) -> None:
        from qdrant_client import AsyncQdrantClient  # type: ignore[import-untyped]

        self._client = AsyncQdrantClient(
            url=url,
            api_key=api_key or None,
        )
        self._collection = collection
        self._dimensions = embedding_dimensions

    async def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]

        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dimensions,
                    distance=Distance.COSINE,
                ),
            )
            log.info("store.qdrant.collection_created", collection=self._collection)

    async def upsert(
        self,
        document_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        from qdrant_client.models import PointStruct  # type: ignore[import-untyped]

        points = [
            PointStruct(
                id=_str_to_uint64(c["id"]),
                vector=c["embedding"],
                payload={
                    "chunk_id": c["id"],
                    "document_id": document_id,
                    "user_id": user_id,
                    "content": c["content"],
                    "page_number": c.get("page_number"),
                    "chunk_index": c["chunk_index"],
                    "token_count": c["token_count"],
                    "metadata": c.get("metadata", {}),
                },
            )
            for c in chunks
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        log.debug("store.qdrant.upserted", count=len(points), document_id=document_id)

    async def search(
        self,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        top_k: int,
        similarity_threshold: float = 0.35,
    ) -> list[VectorSearchResult]:
        if not document_ids:
            log.error("store.qdrant.empty_document_ids_rejected", user_id=user_id)
            return []
        if not user_id:
            log.error("store.qdrant.empty_user_id_rejected")
            return []
        from qdrant_client.models import Filter, FieldCondition, MatchAny  # type: ignore[import-untyped]

        query_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchAny(any=[user_id])),
                FieldCondition(key="document_id", match=MatchAny(any=document_ids)),
            ]
        )

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=similarity_threshold,
            with_payload=True,
        )

        return [
            VectorSearchResult(
                chunk_id=r.payload["chunk_id"],
                document_id=r.payload["document_id"],
                content=r.payload["content"],
                page_number=r.payload.get("page_number"),
                chunk_index=r.payload.get("chunk_index", 0),
                score=float(r.score),
                metadata=r.payload.get("metadata", {}),
            )
            for r in results
        ]

    async def delete(self, document_id: str) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore[import-untyped]

        await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )
        log.debug("store.qdrant.deleted", document_id=document_id)
