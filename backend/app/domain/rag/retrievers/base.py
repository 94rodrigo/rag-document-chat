from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    page_number: int | None
    chunk_index: int
    score: float
    retrieval_method: str
    rerank_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def final_score(self) -> float:
        return self.rerank_score if self.rerank_score is not None else self.score


class RetrieverProtocol(Protocol):
    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        document_names: dict[str, str],
        top_k: int,
        similarity_threshold: float,
    ) -> list[RetrievedChunk]: ...
