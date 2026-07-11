from __future__ import annotations

from typing import Protocol


class EmbedderProtocol(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
