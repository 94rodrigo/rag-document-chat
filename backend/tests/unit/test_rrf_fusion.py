from __future__ import annotations

import pytest

from app.domain.rag.retrievers.hybrid import _RRF_K, HybridRetriever, _rrf_fuse
from tests.conftest import make_chunk


def rrf_score(*ranks: int, k: int = _RRF_K) -> float:
    """Expected RRF contribution for a chunk appearing at the given 0-based ranks."""
    return sum(1.0 / (k + rank + 1) for rank in ranks)


class TestRRFScoring:
    def test_single_list_scores_follow_reciprocal_rank(self) -> None:
        dense = [make_chunk("a"), make_chunk("b"), make_chunk("c")]

        fused = _rrf_fuse({"dense": dense}, top_k=3)

        assert [c.chunk_id for c in fused] == ["a", "b", "c"]
        assert fused[0].score == pytest.approx(rrf_score(0))
        assert fused[1].score == pytest.approx(rrf_score(1))
        assert fused[2].score == pytest.approx(rrf_score(2))

    def test_chunk_in_both_lists_sums_contributions(self) -> None:
        shared = make_chunk("shared")
        dense = [make_chunk("d0"), shared]
        bm25 = [make_chunk("b0"), make_chunk("shared")]

        fused = _rrf_fuse({"dense": dense, "bm25": bm25}, top_k=10)

        by_id = {c.chunk_id: c for c in fused}
        # rank 1 in dense + rank 1 in bm25
        assert by_id["shared"].score == pytest.approx(rrf_score(1, 1))
        assert by_id["d0"].score == pytest.approx(rrf_score(0))
        assert by_id["b0"].score == pytest.approx(rrf_score(0))

    def test_consensus_outranks_single_list_leader(self) -> None:
        """The defining property of RRF: a chunk both retrievers agree on beats one
        that only a single retriever ranked first."""
        dense = [make_chunk("dense_top"), make_chunk("agreed")]
        bm25 = [make_chunk("bm25_top"), make_chunk("agreed")]

        fused = _rrf_fuse({"dense": dense, "bm25": bm25}, top_k=10)

        assert fused[0].chunk_id == "agreed"
        assert fused[0].score > fused[1].score

    def test_higher_k_compresses_rank_differences(self) -> None:
        # Fresh chunks per call: _rrf_fuse rewrites chunk.score in place, so sharing
        # objects between the two fusions would have the second overwrite the first.
        tight = _rrf_fuse({"dense": [make_chunk("a"), make_chunk("b")]}, top_k=2, k=1)
        loose = _rrf_fuse({"dense": [make_chunk("a"), make_chunk("b")]}, top_k=2, k=1000)

        tight_gap = tight[0].score - tight[1].score
        loose_gap = loose[0].score - loose[1].score
        assert tight_gap > loose_gap

    def test_fusion_mutates_the_chunks_it_is_given(self) -> None:
        """Documents a sharp edge: fusion rewrites score/retrieval_method on the input
        objects rather than returning copies, so retriever results must not be reused
        across fusions."""
        chunk = make_chunk("a", score=0.99)

        fused = _rrf_fuse({"dense": [chunk]}, top_k=1)

        assert fused[0] is chunk
        assert chunk.score == pytest.approx(rrf_score(0))
        assert chunk.retrieval_method == "hybrid"


class TestRRFFusionBehaviour:
    def test_deduplicates_chunks_present_in_both_lists(self) -> None:
        dense = [make_chunk("a"), make_chunk("b")]
        bm25 = [make_chunk("a"), make_chunk("c")]

        fused = _rrf_fuse({"dense": dense, "bm25": bm25}, top_k=10)

        ids = [c.chunk_id for c in fused]
        assert sorted(ids) == ["a", "b", "c"]
        assert len(ids) == len(set(ids))

    def test_truncates_to_top_k(self) -> None:
        dense = [make_chunk(f"c{i}") for i in range(10)]

        fused = _rrf_fuse({"dense": dense}, top_k=3)

        assert len(fused) == 3
        assert [c.chunk_id for c in fused] == ["c0", "c1", "c2"]

    def test_results_are_sorted_by_descending_score(self) -> None:
        dense = [make_chunk(f"d{i}") for i in range(5)]
        bm25 = [make_chunk("d3"), make_chunk("d0")]

        fused = _rrf_fuse({"dense": dense, "bm25": bm25}, top_k=10)

        scores = [c.score for c in fused]
        assert scores == sorted(scores, reverse=True)

    def test_marks_retrieval_method_as_hybrid(self) -> None:
        fused = _rrf_fuse({"dense": [make_chunk("a")]}, top_k=1)

        assert fused[0].retrieval_method == "hybrid"

    def test_overwrites_original_similarity_score(self) -> None:
        """Fused chunks carry the RRF score, not the retriever's raw score."""
        fused = _rrf_fuse({"dense": [make_chunk("a", score=0.99)]}, top_k=1)

        assert fused[0].score == pytest.approx(rrf_score(0))
        assert fused[0].score != 0.99

    def test_empty_results_produce_empty_fusion(self) -> None:
        assert _rrf_fuse({"dense": [], "bm25": []}, top_k=5) == []

    def test_one_empty_retriever_falls_back_to_the_other(self) -> None:
        dense = [make_chunk("a"), make_chunk("b")]

        fused = _rrf_fuse({"dense": dense, "bm25": []}, top_k=5)

        assert [c.chunk_id for c in fused] == ["a", "b"]


class StubRetriever:
    def __init__(self, results: list) -> None:
        self.results = results
        self.calls: list[dict] = []

    async def retrieve(
        self,
        query,
        query_embedding,
        user_id,
        document_ids,
        document_names,
        top_k,
        similarity_threshold,
    ):
        self.calls.append({"query": query, "top_k": top_k})
        return self.results


class TestHybridRetriever:
    async def test_fuses_both_retrievers_and_respects_top_k(self) -> None:
        dense = StubRetriever([make_chunk("a"), make_chunk("shared")])
        bm25 = StubRetriever([make_chunk("b"), make_chunk("shared")])
        retriever = HybridRetriever(dense=dense, bm25=bm25)

        results = await retriever.retrieve(
            query="q",
            query_embedding=[0.1, 0.2],
            user_id="user-1",
            document_ids=["doc-1"],
            document_names={"doc-1": "doc.pdf"},
            top_k=2,
            similarity_threshold=0.0,
        )

        assert len(results) == 2
        assert results[0].chunk_id == "shared"
        assert all(c.retrieval_method == "hybrid" for c in results)

    async def test_overfetches_three_times_top_k_from_each_retriever(self) -> None:
        """Each retriever is asked for more candidates than top_k so fusion has
        material to work with."""
        dense = StubRetriever([])
        bm25 = StubRetriever([])
        retriever = HybridRetriever(dense=dense, bm25=bm25)

        await retriever.retrieve(
            query="q",
            query_embedding=[0.1],
            user_id="user-1",
            document_ids=["doc-1"],
            document_names={},
            top_k=5,
            similarity_threshold=0.0,
        )

        assert dense.calls[0]["top_k"] == 15
        assert bm25.calls[0]["top_k"] == 15
