from __future__ import annotations

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger(__name__)

_BATCH_SIZE = 100


class OpenAIEmbedder:
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        import openai

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=text.replace("\n", " "),
            dimensions=self._dimensions,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ") for t in texts]
        results: list[list[float]] = []

        for i in range(0, len(cleaned), _BATCH_SIZE):
            batch = cleaned[i : i + _BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
                dimensions=self._dimensions,
            )
            batch_embeddings = [d.embedding for d in sorted(response.data, key=lambda x: x.index)]
            results.extend(batch_embeddings)

        return results
