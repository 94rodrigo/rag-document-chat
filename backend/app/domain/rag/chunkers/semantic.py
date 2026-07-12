from __future__ import annotations

import structlog

from app.domain.rag.chunkers.base import TextChunk, count_tokens, get_tokenizer, split_sentences
from app.domain.rag.embedders.base import EmbedderProtocol

log = structlog.get_logger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticChunker:
    """
    Groups sentences by semantic similarity. Finds breakpoints where consecutive
    sentence embeddings diverge beyond a threshold percentile, then merges
    groups into size-bounded chunks.
    """

    def __init__(
        self,
        embedder: EmbedderProtocol,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        breakpoint_percentile: float = 95.0,
    ) -> None:
        self._embedder = embedder
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._breakpoint_percentile = breakpoint_percentile
        self._tokenizer = get_tokenizer()

    async def chunk(self, pages: list[tuple[int | None, str]]) -> list[TextChunk]:
        full_text = "\n\n".join(text for _, text in pages if text.strip())
        sentences = split_sentences(full_text)

        if not sentences:
            return []

        if len(sentences) == 1:
            tokens = count_tokens(sentences[0], self._tokenizer)
            return [TextChunk(content=sentences[0], chunk_index=0, token_count=tokens)]

        embeddings = await self._embedder.embed_batch(sentences)

        distances = [
            1.0 - _cosine_similarity(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ]

        threshold = _percentile(distances, self._breakpoint_percentile)
        breakpoints = {i for i, d in enumerate(distances) if d > threshold}

        groups: list[list[str]] = []
        current: list[str] = [sentences[0]]
        for i, sentence in enumerate(sentences[1:], start=0):
            if i in breakpoints:
                groups.append(current)
                current = []
            current.append(sentence)
        groups.append(current)

        chunks: list[TextChunk] = []
        for group in groups:
            group_text = " ".join(group)
            sub = self._split_oversized(group_text)
            for text in sub:
                chunks.append(
                    TextChunk(
                        content=text,
                        chunk_index=len(chunks),
                        token_count=count_tokens(text, self._tokenizer),
                        page_number=None,
                    )
                )

        log.debug(
            "chunker.semantic.done",
            sentences=len(sentences),
            breakpoints=len(breakpoints),
            chunks=len(chunks),
        )
        return chunks

    def _split_oversized(self, text: str) -> list[str]:
        """Fall back to token splitting for groups that exceed chunk_size."""
        if count_tokens(text, self._tokenizer) <= self._chunk_size:
            return [text]

        tokens = self._tokenizer.encode(text)
        parts: list[str] = []
        step = self._chunk_size - self._chunk_overlap
        for i in range(0, len(tokens), step):
            window = tokens[i : i + self._chunk_size]
            parts.append(self._tokenizer.decode(window))
        return parts


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = (p / 100.0) * (len(sorted_vals) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_vals) - 1)
    frac = idx - lower
    return sorted_vals[lower] * (1 - frac) + sorted_vals[upper] * frac
