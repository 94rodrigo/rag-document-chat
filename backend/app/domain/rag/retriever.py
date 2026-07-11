from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from app.config import get_settings
from app.domain.documents.repository import ChunkRepository

log = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    page_number: int | None
    score: float
    chunk_index: int


class Retriever:
    """Vector similarity retrieval with optional MMR re-ranking."""

    def __init__(self, chunk_repo: ChunkRepository) -> None:
        self._repo = chunk_repo

    async def retrieve(
        self,
        query_embedding: list[float],
        user_id: str,
        document_ids: list[str],
        top_k: int = settings.rag_top_k,
        similarity_threshold: float = settings.rag_similarity_threshold,
        document_names: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks via cosine similarity, optionally filtered."""
        raw = await self._repo.similarity_search(
            query_embedding=query_embedding,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k * 2,  # over-fetch for MMR
            similarity_threshold=similarity_threshold,
        )

        if not raw:
            log.info("retriever.no_results", user_id=user_id, doc_count=len(document_ids))
            return []

        # MMR re-rank to maximise relevance and diversity
        reranked = self._mmr_rerank(raw, top_k=top_k)

        doc_names = document_names or {}
        results = [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc_names.get(chunk.document_id, "Unknown document"),
                content=chunk.content,
                page_number=chunk.page_number,
                score=score,
                chunk_index=chunk.chunk_index,
            )
            for chunk, score in reranked
        ]

        log.info(
            "retriever.results",
            count=len(results),
            top_score=results[0].score if results else 0,
        )
        return results

    @staticmethod
    def _mmr_rerank(
        candidates: list[tuple[Any, float]],
        top_k: int,
        lambda_param: float = 0.6,
    ) -> list[tuple[Any, float]]:
        """
        Maximal Marginal Relevance re-ranking.
        Balances relevance vs. diversity to reduce redundant chunks.
        """
        if len(candidates) <= top_k:
            return candidates

        selected: list[tuple[Any, float]] = []
        remaining = list(candidates)

        # Greedily pick candidates maximising: λ*relevance - (1-λ)*max_similarity_to_selected
        while len(selected) < top_k and remaining:
            if not selected:
                best = max(remaining, key=lambda x: x[1])
                selected.append(best)
                remaining.remove(best)
                continue

            best_candidate = None
            best_score = float("-inf")

            for candidate in remaining:
                chunk, relevance = candidate
                # Approximate redundancy by text overlap (jaccard on trigrams)
                max_sim = max(
                    _trigram_similarity(chunk.content, sel_chunk.content)
                    for sel_chunk, _ in selected
                )
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate

            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)

        return selected


def _trigram_similarity(a: str, b: str) -> float:
    """Fast character trigram Jaccard similarity."""
    def trigrams(s: str) -> set[str]:
        s = s.lower()[:200]  # limit for performance
        return {s[i:i+3] for i in range(len(s) - 2)}

    tg_a = trigrams(a)
    tg_b = trigrams(b)
    if not tg_a or not tg_b:
        return 0.0
    intersection = len(tg_a & tg_b)
    union = len(tg_a | tg_b)
    return intersection / union if union else 0.0
