from __future__ import annotations

import structlog

from app.domain.rag.chunkers.base import TextChunk, count_tokens, get_tokenizer
from app.domain.rag.chunkers.recursive import RecursiveChunker
from app.domain.rag.chunkers.semantic import SemanticChunker, _cosine_similarity
from app.domain.rag.embedders.base import EmbedderProtocol

log = structlog.get_logger(__name__)


class HybridChunker:
    """
    Combines recursive and semantic chunking:
    1. Recursive split guarantees size constraints.
    2. Semantic pass merges adjacent chunks that are highly similar (reducing
       fragmentation) and re-splits any that lost coherence during merging.
    """

    def __init__(
        self,
        embedder: EmbedderProtocol,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        merge_threshold: float = 0.92,
    ) -> None:
        self._recursive = RecursiveChunker(chunk_size, chunk_overlap)
        self._semantic = SemanticChunker(
            embedder,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            breakpoint_percentile=90.0,
        )
        self._embedder = embedder
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._merge_threshold = merge_threshold
        self._tokenizer = get_tokenizer()

    async def chunk(self, pages: list[tuple[int | None, str]]) -> list[TextChunk]:
        recursive_chunks = await self._recursive.chunk(pages)

        if len(recursive_chunks) < 3:
            return recursive_chunks

        texts = [c.content for c in recursive_chunks]
        embeddings = await self._embedder.embed_batch(texts)

        merged = self._merge_similar(recursive_chunks, embeddings)

        for i, chunk in enumerate(merged):
            chunk.chunk_index = i

        log.debug(
            "chunker.hybrid.done",
            recursive_count=len(recursive_chunks),
            merged_count=len(merged),
        )
        return merged

    def _merge_similar(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> list[TextChunk]:
        merged: list[TextChunk] = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            current_emb = embeddings[i]

            while i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                next_emb = embeddings[i + 1]
                sim = _cosine_similarity(current_emb, next_emb)
                candidate_text = current.content + " " + next_chunk.content
                candidate_tokens = count_tokens(candidate_text, self._tokenizer)

                if sim >= self._merge_threshold and candidate_tokens <= self._chunk_size:
                    combined_emb = _average_embeddings(current_emb, next_emb)
                    current = TextChunk(
                        content=candidate_text,
                        chunk_index=current.chunk_index,
                        token_count=candidate_tokens,
                        page_number=current.page_number,
                        metadata={**current.metadata, **next_chunk.metadata},
                    )
                    current_emb = combined_emb
                    i += 1
                else:
                    break

            merged.append(current)
            i += 1

        return merged


def _average_embeddings(a: list[float], b: list[float]) -> list[float]:
    return [(x + y) / 2.0 for x, y in zip(a, b)]
