"""RRF(Reciprocal Rank Fusion) — 서로 다른 두 검색 결과(의미기반/키워드기반)의 순위만
가지고 점수를 합친다. 점수 스케일이 전혀 다른 두 방식(코사인 유사도 vs BM25 점수)을
그대로 더하면 한쪽이 지배해버리는 문제를, 절대 점수 대신 '몇 등이었는지'만 써서 피한다."""


def reciprocal_rank_fusion(ranked_lists: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """ranked_lists: 각 검색 방식이 반환한 '청크 인덱스' 순위 리스트들 (1등부터 순서대로).
    반환: (청크 인덱스, 합산 RRF 점수)를 점수 내림차순으로."""
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_index in enumerate(ranked):
            scores[chunk_index] = scores.get(chunk_index, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
