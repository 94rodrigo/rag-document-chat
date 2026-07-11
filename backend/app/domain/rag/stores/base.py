from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class VectorSearchResult:
    chunk_id: str
    document_id: str
    content: str
    page_number: int | None
    chunk_index: int
    score: float
    metadata: dict[str, Any]


class VectorStoreProtocol(Protocol):
    async def upsert(
        self,
        document_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """
        chunks: list of dicts with keys:
            id, content, embedding, page_number, chunk_index,
            token_count, metadata
        """
        ...

    async def search(
        self,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        top_k: int,
        similarity_threshold: float,
    ) -> list[VectorSearchResult]: ...

    async def delete(self, document_id: str) -> None: ...
