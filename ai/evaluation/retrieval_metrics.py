"""검색 품질 지표 — Recall@k, MRR. 임베딩/하이브리드 검색 비교에 공통으로 쓴다."""


def recall_at_k(ranked_ids: list[str], relevant_id: str, k: int) -> int:
    """ranked_ids 상위 k개 안에 relevant_id가 있으면 1, 없으면 0."""
    return 1 if relevant_id in ranked_ids[:k] else 0


def reciprocal_rank(ranked_ids: list[str], relevant_id: str) -> float:
    """relevant_id의 순위 역수(1위=1.0, 2위=0.5, ...). 못 찾으면 0."""
    if relevant_id in ranked_ids:
        return 1.0 / (ranked_ids.index(relevant_id) + 1)
    return 0.0
