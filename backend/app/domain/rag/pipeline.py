from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag.chunkers.base import TextChunk
from app.domain.rag.embedders.base import EmbedderProtocol
from app.domain.rag.parsers.base import ParsedDocument
from app.domain.rag.reranker import CrossEncoderReranker
from app.domain.rag.retrievers.base import RetrievedChunk
from app.domain.rag.stores.base import VectorStoreProtocol
from app.shared.utils import generate_id

log = structlog.get_logger(__name__)


class ChunkerType(StrEnum):
    recursive = "recursive"
    semantic = "semantic"
    hybrid = "hybrid"


class EmbedderType(StrEnum):
    openai = "openai"
    voyage = "voyage"
    bge = "bge"


class RetrieverType(StrEnum):
    dense = "dense"
    bm25 = "bm25"
    hybrid = "hybrid"


class VectorStoreType(StrEnum):
    pgvector = "pgvector"
    qdrant = "qdrant"


@dataclass
class RAGPipelineConfig:
    chunker_type: ChunkerType = ChunkerType.hybrid
    chunk_size: int = 512
    chunk_overlap: int = 64
    retriever_type: RetrieverType = RetrieverType.hybrid
    pre_rerank_top_k: int = 20
    rerank_enabled: bool = True
    rerank_top_k: int = 6
    similarity_threshold: float = 0.35


class RAGPipeline:
    """
    Wires all RAG components together. Provides two entry points:
    - index_document(): parse → chunk → embed → store
    - retrieve_and_rerank(): embed query → retrieve → rerank
    """

    def __init__(
        self,
        config: RAGPipelineConfig,
        embedder: EmbedderProtocol,
        vector_store: VectorStoreProtocol,
        session: AsyncSession,
        reranker: CrossEncoderReranker | None = None,
    ) -> None:
        self._config = config
        self._embedder = embedder
        self._store = vector_store
        self._session = session
        self._reranker = reranker

        self._chunker = self._build_chunker()
        self._retriever = self._build_retriever()

    def _build_chunker(self) -> Any:
        ct = self._config.chunker_type
        size = self._config.chunk_size
        overlap = self._config.chunk_overlap

        if ct == ChunkerType.recursive:
            from app.domain.rag.chunkers.recursive import RecursiveChunker
            return RecursiveChunker(chunk_size=size, chunk_overlap=overlap)

        if ct == ChunkerType.semantic:
            from app.domain.rag.chunkers.semantic import SemanticChunker
            return SemanticChunker(self._embedder, chunk_size=size, chunk_overlap=overlap)

        from app.domain.rag.chunkers.hybrid import HybridChunker
        return HybridChunker(self._embedder, chunk_size=size, chunk_overlap=overlap)

    def _build_retriever(self) -> Any:
        rt = self._config.retriever_type

        if rt == RetrieverType.dense:
            from app.domain.rag.retrievers.dense import DenseRetriever
            return DenseRetriever(self._store)

        if rt == RetrieverType.bm25:
            from app.domain.rag.retrievers.bm25 import BM25Retriever
            return BM25Retriever(self._session)

        from app.domain.rag.retrievers.bm25 import BM25Retriever
        from app.domain.rag.retrievers.dense import DenseRetriever
        from app.domain.rag.retrievers.hybrid import HybridRetriever

        dense = DenseRetriever(self._store)
        bm25 = BM25Retriever(self._session)
        return HybridRetriever(dense, bm25)

    async def index_document(
        self,
        parsed: ParsedDocument,
        document_id: str,
        user_id: str,
        batch_size: int = 100,
    ) -> list[TextChunk]:
        """Parse → chunk → embed → store. Returns the TextChunks that were indexed."""
        pages = [(p.page_number, p.content) for p in parsed.pages]
        text_chunks = await self._chunker.chunk(pages)

        if not text_chunks:
            log.warning("pipeline.index.empty", document_id=document_id)
            return []

        log.info(
            "pipeline.index.chunked",
            document_id=document_id,
            chunks=len(text_chunks),
        )

        all_embeddings: list[list[float]] = []
        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i : i + batch_size]
            texts = [c.content for c in batch]
            batch_embeddings = await self._embedder.embed_batch(texts)
            all_embeddings.extend(batch_embeddings)

        store_chunks = [
            {
                "id": generate_id(),
                "content": chunk.content,
                "embedding": embedding,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            for chunk, embedding in zip(text_chunks, all_embeddings, strict=True)
        ]

        await self._store.upsert(document_id, user_id, store_chunks)

        log.info(
            "pipeline.index.complete",
            document_id=document_id,
            chunks=len(store_chunks),
        )
        return text_chunks

    async def retrieve_and_rerank(
        self,
        query: str,
        user_id: str,
        document_ids: list[str],
        document_names: dict[str, str],
    ) -> list[RetrievedChunk]:
        """Embed query → retrieve → optional rerank. Returns final ranked chunks."""
        query_embedding = await self._embedder.embed(query)

        chunks = await self._retriever.retrieve(
            query=query,
            query_embedding=query_embedding,
            user_id=user_id,
            document_ids=document_ids,
            document_names=document_names,
            top_k=self._config.pre_rerank_top_k,
            similarity_threshold=self._config.similarity_threshold,
        )

        if not chunks:
            # Threshold filtered everything (common for meta/summarization queries).
            # Retry without threshold — best-available chunks are still useful context.
            log.info("pipeline.retrieve.threshold_fallback", query_len=len(query))
            chunks = await self._retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                user_id=user_id,
                document_ids=document_ids,
                document_names=document_names,
                top_k=self._config.rerank_top_k,
                similarity_threshold=0.0,
            )

        if not chunks:
            return []

        if self._config.rerank_enabled and self._reranker is not None:
            chunks = await self._reranker.rerank(
                query=query,
                chunks=chunks,
                top_k=self._config.rerank_top_k,
            )
        else:
            chunks = chunks[: self._config.rerank_top_k]

        log.info(
            "pipeline.retrieve.complete",
            query_len=len(query),
            chunks_returned=len(chunks),
            top_score=chunks[0].final_score if chunks else 0,
        )
        return chunks


def build_pipeline(
    session: AsyncSession,
    config: RAGPipelineConfig | None = None,
) -> RAGPipeline:
    """Factory that wires the pipeline from application settings."""
    from app.config import get_settings
    from app.domain.rag.embedders.registry import get_embedder

    settings = get_settings()
    cfg = config or _config_from_settings(settings)
    embedder = get_embedder()
    store = _build_store(settings, session)
    reranker = CrossEncoderReranker(settings.rag_rerank_model) if settings.rag_rerank_enabled else None

    return RAGPipeline(
        config=cfg,
        embedder=embedder,
        vector_store=store,
        session=session,
        reranker=reranker,
    )


def _config_from_settings(settings: Any) -> RAGPipelineConfig:
    return RAGPipelineConfig(
        chunker_type=ChunkerType(settings.rag_chunker.value),
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        retriever_type=RetrieverType(settings.rag_retriever.value),
        pre_rerank_top_k=settings.rag_pre_rerank_top_k,
        rerank_enabled=settings.rag_rerank_enabled,
        rerank_top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )


def _build_store(settings: Any, session: AsyncSession) -> VectorStoreProtocol:
    store_type = settings.rag_vector_store.value

    if store_type == "qdrant":
        from app.domain.rag.stores.qdrant import QdrantStore

        return QdrantStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            api_key=settings.qdrant_api_key,
            embedding_dimensions=settings.rag_embedding_dimensions,
        )

    from app.domain.rag.stores.pgvector import PgVectorStore
    return PgVectorStore(session)
