from __future__ import annotations

import pytest

from app.domain.rag.chunkers.base import count_tokens, get_tokenizer, split_sentences
from app.domain.rag.chunkers.recursive import RecursiveChunker

TOKENIZER = get_tokenizer()


def tokens(text: str) -> int:
    return count_tokens(text, TOKENIZER)


PARAGRAPH = (
    "Retrieval augmented generation grounds a language model in source documents. "
    "It retrieves relevant passages before generating an answer. "
    "This reduces hallucination and lets the model cite its sources.\n\n"
    "Chunking splits a document into passages small enough to embed. "
    "Chunks that are too large dilute the embedding signal. "
    "Chunks that are too small lose the surrounding context.\n\n"
    "Hybrid retrieval combines dense vectors with keyword matching. "
    "Dense search captures meaning while keyword search captures rare terms."
)


class TestRecursiveChunkerInvariants:
    async def test_every_chunk_respects_the_token_limit(self) -> None:
        """The chunker's core contract: no chunk exceeds chunk_size tokens."""
        chunker = RecursiveChunker(chunk_size=32, chunk_overlap=8)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        assert chunks
        oversized = [c for c in chunks if tokens(c.content) > 32]
        assert oversized == [], (
            f"{len(oversized)} chunk(s) exceeded the 32-token limit: "
            f"{[tokens(c.content) for c in oversized]}"
        )

    async def test_reported_token_count_matches_actual_content(self) -> None:
        chunker = RecursiveChunker(chunk_size=48, chunk_overlap=8)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        for chunk in chunks:
            assert chunk.token_count == tokens(chunk.content)

    async def test_no_content_is_dropped(self) -> None:
        chunker = RecursiveChunker(chunk_size=32, chunk_overlap=0)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        joined = " ".join(c.content for c in chunks)
        for word in ("hallucination", "Chunking", "Hybrid", "keyword"):
            assert word in joined

    async def test_text_longer_than_chunk_size_produces_multiple_chunks(self) -> None:
        chunker = RecursiveChunker(chunk_size=16, chunk_overlap=4)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        assert len(chunks) > 1


class TestRecursiveChunkerIndexing:
    async def test_chunk_index_is_globally_sequential_across_pages(self) -> None:
        chunker = RecursiveChunker(chunk_size=24, chunk_overlap=4)

        chunks = await chunker.chunk([(1, PARAGRAPH), (2, PARAGRAPH), (3, PARAGRAPH)])

        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    async def test_page_number_is_preserved_per_chunk(self) -> None:
        chunker = RecursiveChunker(chunk_size=24, chunk_overlap=4)

        chunks = await chunker.chunk([(1, PARAGRAPH), (2, PARAGRAPH)])

        pages = {c.page_number for c in chunks}
        assert pages == {1, 2}
        # Page 1's chunks all precede page 2's.
        page_sequence = [c.page_number for c in chunks]
        assert page_sequence == sorted(page_sequence)

    async def test_pages_without_text_are_skipped(self) -> None:
        chunker = RecursiveChunker(chunk_size=64, chunk_overlap=8)

        chunks = await chunker.chunk(
            [(1, "Real content on the first page."), (2, "   \n\n  "), (3, "")]
        )

        assert {c.page_number for c in chunks} == {1}
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    async def test_empty_input_yields_no_chunks(self) -> None:
        chunker = RecursiveChunker()

        assert await chunker.chunk([]) == []
        assert await chunker.chunk([(1, "")]) == []


class TestRecursiveChunkerOverlap:
    async def test_consecutive_chunks_share_overlapping_text(self) -> None:
        chunker = RecursiveChunker(chunk_size=32, chunk_overlap=16)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        assert len(chunks) > 1
        # With a generous overlap budget, adjacent chunks should share at least one
        # sentence fragment.
        overlapping_pairs = 0
        for prev, nxt in zip(chunks, chunks[1:], strict=False):
            prev_words = set(prev.content.split())
            next_words = set(nxt.content.split())
            if prev_words & next_words:
                overlapping_pairs += 1
        assert overlapping_pairs > 0

    async def test_zero_overlap_produces_disjoint_adjacent_chunks(self) -> None:
        chunker = RecursiveChunker(chunk_size=32, chunk_overlap=0)

        chunks = await chunker.chunk([(1, PARAGRAPH)])

        for prev, nxt in zip(chunks, chunks[1:], strict=False):
            assert prev.content != nxt.content


class TestSentenceSplitter:
    def test_splits_on_terminal_punctuation(self) -> None:
        sentences = split_sentences("First one. Second one! Third one?")

        assert sentences == ["First one.", "Second one!", "Third one?"]

    def test_splits_across_paragraphs(self) -> None:
        sentences = split_sentences("Para one line.\n\nPara two line.")

        assert sentences == ["Para one line.", "Para two line."]

    def test_does_not_split_on_decimal_points(self) -> None:
        sentences = split_sentences("The score was 3.5 out of 5. Good result.")

        assert sentences == ["The score was 3.5 out of 5.", "Good result."]

    def test_drops_blank_segments(self) -> None:
        sentences = split_sentences("Only one.\n\n\n\n   \n\n")

        assert sentences == ["Only one."]

    def test_empty_text_yields_no_sentences(self) -> None:
        assert split_sentences("") == []
        assert split_sentences("   \n\n  ") == []


@pytest.mark.parametrize("chunk_size", [16, 32, 64, 128])
async def test_token_limit_holds_across_chunk_sizes(chunk_size: int) -> None:
    chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_size // 4)

    chunks = await chunker.chunk([(1, PARAGRAPH * 3)])

    assert chunks
    assert all(tokens(c.content) <= chunk_size for c in chunks)
