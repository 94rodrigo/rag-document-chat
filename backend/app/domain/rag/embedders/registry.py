from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.domain.rag.embedders.base import EmbedderProtocol

if TYPE_CHECKING:
    from app.config import Settings


@lru_cache(maxsize=1)
def get_embedder(settings: Settings | None = None) -> EmbedderProtocol:
    from app.config import get_settings

    s = settings or get_settings()

    provider = s.rag_embedder.value

    if provider == "openai":
        from app.domain.rag.embedders.openai import OpenAIEmbedder

        return OpenAIEmbedder(
            api_key=s.openai_api_key,
            model=s.openai_embedding_model,
            dimensions=s.rag_embedding_dimensions,
        )

    if provider == "voyage":
        from app.domain.rag.embedders.voyage import VoyageAIEmbedder

        return VoyageAIEmbedder(
            api_key=s.voyage_api_key,
            model=s.voyage_embedding_model,
        )

    if provider == "bge":
        from app.domain.rag.embedders.bge import BGEEmbedder

        return BGEEmbedder(
            model_name=s.bge_model_name,
            device=s.bge_device,
        )

    raise ValueError(f"Unknown embedder provider: {provider}")
