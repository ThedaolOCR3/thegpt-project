"""사용자 질의 → Neon(pgvector)에서 provider별로 검색 → RRF 결합 → (옵션) reranker.

`ai/rag/pipeline.retrieve()`와 같은 알고리즘이지만, 검색 대상이 메모리의 Chunk
리스트가 아니라 DB 테이블 전체라는 점이 다르다 — DB 세션이 필요해서 ai/rag 안에는
못 둔다(루트 CLAUDE.md 원칙).

임베딩 provider는 이 서비스를 호출하는 쪽(또는 모듈 기본값)이 정한다 — 팀원이 실제
모델을 확정하면 `search()`의 `providers=` 인자만 바꾸면 된다.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from ai.rag import EmbeddingProvider, RetrievedChunk, hybrid
from ai.rag.reranker import rerank as rerank_candidates
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rag_embedding import get_default_rag_embedding_providers
from app.models.generated import DocumentChunks
from app.repositories.document_chunk import DocumentChunkRepository

logger = get_logger("services.rag_search")

# 최종 top_k보다 넉넉히 뽑아서 RRF/reranker 후보 풀을 만든다 — 최소 후보 수는
# EMBEDDING_SEARCH_CANDIDATES로 조정 가능(config.py 참고).
_CANDIDATE_MULTIPLIER = 4


def search(
    db: Session,
    query: str,
    top_k: int = 5,
    use_reranker: bool = False,
    providers: list[EmbeddingProvider] | None = None,
) -> list[RetrievedChunk]:
    if not query.strip():
        return []

    providers = providers or get_default_rag_embedding_providers()
    candidate_k = max(top_k * _CANDIDATE_MULTIPLIER, settings.embedding_search_candidates)
    repo = DocumentChunkRepository(db)

    rows_by_id: dict[UUID, DocumentChunks] = {}
    ranked_lists: list[list[UUID]] = []

    for provider in providers:
        query_vector = provider.embed_query(query)
        hits = repo.search_by_provider(provider.name, query_vector, candidate_k)
        ranked_lists.append([chunk.id for chunk, _distance in hits])
        for chunk, _distance in hits:
            rows_by_id[chunk.id] = chunk

    if not rows_by_id:
        logger.warning("rag_search: 검색 결과 없음 (모든 provider 0건) query=%r", query)
        return []

    fused = hybrid.reciprocal_rank_fusion(ranked_lists, k=settings.embedding_rrf_k)

    if use_reranker and fused:
        candidate_ids = [chunk_id for chunk_id, _ in fused[: max(top_k * 3, top_k)]]
        candidate_texts = [rows_by_id[cid].chunk_text for cid in candidate_ids]
        reranked = rerank_candidates(query, candidate_texts)
        ordered = [(candidate_ids[i], score) for i, score in reranked]
    else:
        ordered = fused

    results: list[RetrievedChunk] = []
    for position, (chunk_id, score) in enumerate(ordered[:top_k]):
        row = rows_by_id[chunk_id]
        results.append(
            RetrievedChunk(
                index=position,
                text=row.chunk_text,
                score=float(score),
                chunk_id=str(row.id),
                document_id=str(row.document_id),
            )
        )
    return results
