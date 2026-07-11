from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import structlog

log = structlog.get_logger(__name__)

_BATCH_SIZE = 128
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="voyage")

_MODEL_DIMS: dict[str, int] = {
    "voyage-3": 1024,
    "voyage-3-large": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
    "voyage-finance-2": 1024,
    "voyage-law-2": 1024,
}


class VoyageAIEmbedder:
    """
    VoyageAI embedder. Uses the synchronous voyageai client wrapped in a
    thread pool because voyageai does not provide an async interface.
    """

    def __init__(self, api_key: str, model: str = "voyage-3") -> None:
        import voyageai  # type: ignore[import-untyped]

        self._client = voyageai.Client(api_key=api_key)
        self._model = model
        self._dimensions = _MODEL_DIMS.get(model, 1024)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        results: list[list[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await loop.run_in_executor(
                _EXECUTOR, self._embed_sync, batch
            )
            results.extend(embeddings)

        return results

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embed(texts, model=self._model)
        return [e for e in response.embeddings]
