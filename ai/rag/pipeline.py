"""RAG 검색 파이프라인 오케스트레이션 — 로컬 랩과 향후 ai/consultation이 공통으로 쓴다.

흐름: 청크들을 dense(의미)와 keyword(BM25)로 각각 랭킹 -> RRF로 결합 -> (옵션) reranker로 정밀화.
"""
from dataclasses import dataclass

import numpy as np

from . import hybrid, keyword_search
from .chunking import Chunk
from .embedding import embed_query, embed_texts
from .reranker import rerank as rerank_candidates


@dataclass
class RetrievedChunk:
    index: int
    text: str
    score: float


def _rank_by_cosine(query_vector: list[float], chunk_vectors: list[list[float]]) -> list[int]:
    q = np.asarray(query_vector)
    m = np.asarray(chunk_vectors)
    similarities = m @ q  # 임베딩을 normalize해서 만들었으니 내적이 곧 코사인 유사도.
    return np.argsort(-similarities).tolist()


def retrieve(
    chunks: list[Chunk],
    query: str,
    top_k: int = 5,
    use_reranker: bool = False,
) -> list[RetrievedChunk]:
    if not chunks:
        return []

    texts = [c.text for c in chunks]

    chunk_vectors = embed_texts(texts)
    query_vector = embed_query(query)
    dense_ranked = _rank_by_cosine(query_vector, chunk_vectors)

    keyword_hits = keyword_search.search(texts, query, top_k=len(texts))
    keyword_ranked = [i for i, _score in keyword_hits]

    fused = hybrid.reciprocal_rank_fusion([dense_ranked, keyword_ranked])

    if use_reranker and fused:
        candidate_indices = [i for i, _ in fused[: max(top_k * 3, top_k)]]
        candidate_texts = [texts[i] for i in candidate_indices]
        reranked = rerank_candidates(query, candidate_texts)
        ordered = [(candidate_indices[i], score) for i, score in reranked]
    else:
        ordered = fused

    return [RetrievedChunk(index=i, text=texts[i], score=score) for i, score in ordered[:top_k]]
