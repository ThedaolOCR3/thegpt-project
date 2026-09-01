import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.rag_search_service import search


class RagSearchServiceTest(unittest.TestCase):
    def test_jina_and_bge_rankings_are_combined_by_chunk_uuid(self) -> None:
        document_id = uuid4()
        chunk_a = _chunk(document_id, "A")
        chunk_b = _chunk(document_id, "B")
        chunk_c = _chunk(document_id, "C")
        repository = FakeRepository(
            {
                "jina-v4": [chunk_a, chunk_b, chunk_c],
                "medical-bgem3": [chunk_b, chunk_c, chunk_a],
            }
        )

        with patch(
            "app.services.rag_search_service.DocumentChunkRepository",
            return_value=repository,
        ):
            results = search(
                Mock(spec=Session),
                "폐렴 증상",
                top_k=3,
                providers=[
                    FakeProvider("jina-v4", 0.1),
                    FakeProvider("medical-bgem3", 0.2),
                ],
            )

        self.assertEqual([result.text for result in results], ["B", "A", "C"])
        self.assertEqual(repository.requested_limits, [20, 20])
        self.assertEqual(repository.query_heads, [0.1, 0.2])

    def test_search_candidate_count_follows_setting(self) -> None:
        # EMBEDDING_SEARCH_CANDIDATES는 예전엔 코드에 하드코딩된 상수였다 — 설정으로
        # 뺀 뒤에도 실제로 반영되는지 확인.
        repository = FakeRepository({"jina-v4": [_chunk(uuid4(), "A")]})

        with (
            patch("app.services.rag_search_service.DocumentChunkRepository", return_value=repository),
            patch.object(settings, "embedding_search_candidates", 5),
        ):
            search(Mock(spec=Session), "질문", top_k=1, providers=[FakeProvider("jina-v4", 0.1)])

        self.assertEqual(repository.requested_limits, [5])

    def test_rrf_k_follows_setting(self) -> None:
        chunk_a, chunk_b = _chunk(uuid4(), "A"), _chunk(uuid4(), "B")
        repository = FakeRepository(
            {"jina-v4": [chunk_a, chunk_b], "medical-bgem3": [chunk_b, chunk_a]}
        )

        with (
            patch("app.services.rag_search_service.DocumentChunkRepository", return_value=repository),
            patch("app.services.rag_search_service.hybrid.reciprocal_rank_fusion") as mock_rrf,
        ):
            mock_rrf.return_value = [(chunk_a.id, 1.0)]
            with patch.object(settings, "embedding_rrf_k", 5):
                search(
                    Mock(spec=Session),
                    "질문",
                    top_k=1,
                    providers=[FakeProvider("jina-v4", 0.1), FakeProvider("medical-bgem3", 0.2)],
                )

        self.assertEqual(mock_rrf.call_args.kwargs.get("k"), 5)


class FakeProvider:
    dimension = 1024

    def __init__(self, name: str, value: float) -> None:
        self.name = name
        self.value = value

    def embed_query(self, text: str) -> list[float]:
        self.query = text
        return [self.value] * 1024

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError("검색 시에는 문서 Vector를 다시 생성하면 안 됩니다.")


class FakeRepository:
    def __init__(self, rankings: dict[str, list[SimpleNamespace]]) -> None:
        self.rankings = rankings
        self.requested_limits: list[int] = []
        self.query_heads: list[float] = []

    def search_by_provider(self, provider_name, query_vector, top_k):
        self.requested_limits.append(top_k)
        self.query_heads.append(query_vector[0])
        return [
            (chunk, float(rank))
            for rank, chunk in enumerate(self.rankings[provider_name], start=1)
        ]


def _chunk(document_id, text):
    return SimpleNamespace(
        id=uuid4(),
        document_id=document_id,
        chunk_text=text,
    )


if __name__ == "__main__":
    unittest.main()
