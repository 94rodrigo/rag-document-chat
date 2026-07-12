from __future__ import annotations

import structlog

from app.domain.rag.chunkers.base import TextChunk, count_tokens, get_tokenizer

log = structlog.get_logger(__name__)

_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]


class RecursiveChunker:
    """
    Splits text using a hierarchy of separators (paragraph → sentence → word → char).
    Guarantees every chunk is within token limits while maximising semantic coherence.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators or _SEPARATORS
        self._tokenizer = get_tokenizer()

    async def chunk(self, pages: list[tuple[int | None, str]]) -> list[TextChunk]:
        all_chunks: list[TextChunk] = []
        global_index = 0

        for page_number, text in pages:
            if not text.strip():
                continue
            splits = self._split_recursive(text, self._separators)
            merged = self._merge_with_overlap(splits, page_number, global_index)
            all_chunks.extend(merged)
            global_index += len(merged)

        log.debug(
            "chunker.recursive.done",
            pages=len(pages),
            chunks=len(all_chunks),
        )
        return all_chunks

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return self._split_by_tokens(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep and sep not in text:
            return self._split_recursive(text, remaining_seps)

        splits: list[str] = text.split(sep) if sep else list(text)
        good: list[str] = []

        for split in splits:
            split = split.strip()
            if not split:
                continue
            if count_tokens(split, self._tokenizer) <= self._chunk_size:
                good.append(split)
            else:
                good.extend(self._split_recursive(split, remaining_seps))

        return good

    def _split_by_tokens(self, text: str) -> list[str]:
        tokens = self._tokenizer.encode(text)
        chunks: list[str] = []
        for i in range(0, len(tokens), self._chunk_size):
            chunk_tokens = tokens[i : i + self._chunk_size]
            chunks.append(self._tokenizer.decode(chunk_tokens))
        return chunks

    def _merge_with_overlap(
        self,
        splits: list[str],
        page_number: int | None,
        start_index: int,
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        current: list[str] = []

        def window_tokens(parts: list[str]) -> int:
            # Measure the joined text, not the sum of its parts: joining with spaces
            # re-tokenises the boundaries and can cost more tokens than the pieces did
            # separately, which would push the emitted chunk over chunk_size.
            return count_tokens(" ".join(parts), self._tokenizer)

        def flush() -> None:
            if not current:
                return
            text = " ".join(current)
            chunks.append(
                TextChunk(
                    content=text,
                    chunk_index=start_index + len(chunks),
                    token_count=count_tokens(text, self._tokenizer),
                    page_number=page_number,
                )
            )

        for split in splits:
            if current and window_tokens([*current, split]) > self._chunk_size:
                flush()
                # Carry the tail of the flushed window into the next chunk as overlap.
                overlap: list[str] = []
                for s in reversed(current):
                    if window_tokens([s, *overlap]) > self._chunk_overlap:
                        break
                    overlap.insert(0, s)
                # The overlap is a nicety, not a guarantee: drop as much of it as needed
                # so that prepending it cannot push this chunk over chunk_size.
                while overlap and window_tokens([*overlap, split]) > self._chunk_size:
                    overlap.pop(0)
                current = overlap

            current.append(split)

        flush()
        return chunks
