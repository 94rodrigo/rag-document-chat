from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog

from app.domain.rag.retrievers.base import RetrievedChunk

log = structlog.get_logger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="reranker")
_MAX_PASSAGE_TOKENS = 512


class CrossEncoderReranker:
    """
    Re-ranks retrieved chunks using a cross-encoder model.
    The model scores (query, passage) pairs jointly, capturing interaction
    signals that bi-encoder retrieval misses.

    Default model: ms-marco-MiniLM-L-6-v2 (~85 MB, fast, production-quality).
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self._model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

            log.info("reranker.loading_model", model=self._model_name)
            self._model = CrossEncoder(self._model_name)
        return self._model

    def _predict_sync(self, pairs: list[tuple[str, str]]) -> list[float]:
        model = self._get_model()
        scores = model.predict(pairs, show_progress_bar=False)
        if hasattr(scores, "tolist"):
            return scores.tolist()
        return list(scores)

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        pairs = [
            (query, chunk.content[:_MAX_PASSAGE_TOKENS * 4])
            for chunk in chunks
        ]

        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            _EXECUTOR, self._predict_sync, pairs
        )

        ranked = sorted(
            zip(chunks, scores, strict=True),
            key=lambda x: x[1],
            reverse=True,
        )

        result: list[RetrievedChunk] = []
        for chunk, score in ranked[:top_k]:
            chunk.rerank_score = float(score)
            result.append(chunk)

        log.debug(
            "reranker.done",
            input_count=len(chunks),
            output_count=len(result),
            top_score=result[0].rerank_score if result else None,
        )
        return result
