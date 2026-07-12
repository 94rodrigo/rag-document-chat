from __future__ import annotations

import asyncio

import structlog

from app.domain.rag.retrievers.base import RetrievedChunk
from app.domain.rag.retrievers.bm25 import BM25Retriever
from app.domain.rag.retrievers.dense import DenseRetriever

log = structlog.get_logger(__name__)

_RRF_K = 60


class HybridRetriever:
    """
    Reciprocal Rank Fusion of dense vector search and BM25 keyword search.

    RRF score = Σ 1 / (k + rank_i) for each method that returned the chunk.
    k=60 is standard; higher k penalises rank differences less.
    """

    def __init__(self, dense: DenseRetriever, bm25: BM25Retriever) -> None:
        self._dense = dense
        self._bm25 = bm25

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
        fetch_k = top_k * 3

        dense_task = self._dense.retrieve(
            query, query_embedding, user_id, document_ids,
            document_names, fetch_k, similarity_threshold,
        )
        bm25_task = self._bm25.retrieve(
            query, query_embedding, user_id, document_ids,
            document_names, fetch_k, similarity_threshold,
        )

        dense_results, bm25_results = await asyncio.gather(dense_task, bm25_task)

        fused = _rrf_fuse(
            {"dense": dense_results, "bm25": bm25_results},
            top_k=top_k,
        )

        log.debug(
            "retriever.hybrid.done",
            dense_count=len(dense_results),
            bm25_count=len(bm25_results),
            fused_count=len(fused),
        )
        return fused


def _rrf_fuse(
    method_results: dict[str, list[RetrievedChunk]],
    top_k: int,
    k: int = _RRF_K,
) -> list[RetrievedChunk]:
    rrf_scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}

    for _method, results in method_results.items():
        for rank, chunk in enumerate(results):
            cid = chunk.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in chunks:
                chunks[cid] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    fused: list[RetrievedChunk] = []
    for cid in sorted_ids[:top_k]:
        chunk = chunks[cid]
        chunk.score = rrf_scores[cid]
        chunk.retrieval_method = "hybrid"
        fused.append(chunk)

    return fused
