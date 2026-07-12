from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_BATCH_SIZE = 64
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bge")

_MODEL_DIMS: dict[str, int] = {
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-m3": 1024,
}

_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    """
    Local BGE embedder via sentence-transformers. The model is loaded lazily
    and cached in memory. Inference runs in a thread pool to avoid blocking
    the event loop.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._dimensions = _MODEL_DIMS.get(model_name, 1024)
        self._model: Any = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            log.info("embedder.bge.loading_model", model=self._model_name, device=self._device)
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text], is_query=True)
        return results[0]

    async def embed_batch(
        self, texts: list[str], is_query: bool = False
    ) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        results: list[list[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await loop.run_in_executor(
                _EXECUTOR, self._encode_sync, batch, is_query
            )
            results.extend(embeddings)

        return results

    def _encode_sync(self, texts: list[str], is_query: bool) -> list[list[float]]:
        model = self._get_model()
        if is_query:
            texts = [_QUERY_INSTRUCTION + t for t in texts]
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=_BATCH_SIZE,
        )
        return [e.tolist() for e in embeddings]
