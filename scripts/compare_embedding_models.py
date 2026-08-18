"""임베딩 모델 비교 — scripts/eval_data/의 쿼리·코퍼스로 Recall@k, MRR 계산.

먼저 scripts/build_embedding_eval_set.py로 평가셋을 만들어야 한다.
GPU 없이 CPU로 돈다 (sentence-transformers는 CPU 추론 지원).

사용법:
    python scripts/compare_embedding_models.py
    python scripts/compare_embedding_models.py --models "모델A,모델B"
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from ai.evaluation import recall_at_k, reciprocal_rank

EVAL_DIR = Path(__file__).parent / "eval_data"

# 기본 비교 대상: 지금 ai/rag가 실제 쓰는 모델 vs 가볍고 잘 알려진 한국어 대안 모델.
DEFAULT_MODELS = [
    "dragonkue/snowflake-arctic-embed-l-v2.0-ko",  # 현재 프로덕션(ai/rag) 기본값
    "jhgan/ko-sroberta-multitask",  # 비교용 — 더 가벼운 한국어 특화 모델
]

K_VALUES = [1, 5, 10]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate_model(model_name: str, corpus: list[dict], queries: list[dict]) -> dict:
    model = SentenceTransformer(model_name)

    corpus_ids = [row["id"] for row in corpus]
    corpus_texts = [row["text"] for row in corpus]

    t0 = time.time()
    corpus_vectors = np.asarray(model.encode(corpus_texts, normalize_embeddings=True, show_progress_bar=False))
    query_vectors = np.asarray(
        model.encode([q["query"] for q in queries], normalize_embeddings=True, show_progress_bar=False)
    )
    elapsed = time.time() - t0

    recalls = {k: [] for k in K_VALUES}
    rr_scores = []

    sims = query_vectors @ corpus_vectors.T  # 정규화된 벡터라 내적 = 코사인 유사도
    for row_idx, q in enumerate(queries):
        ranked_idx = np.argsort(-sims[row_idx])
        ranked_ids = [corpus_ids[i] for i in ranked_idx]
        for k in K_VALUES:
            recalls[k].append(recall_at_k(ranked_ids, q["relevant_id"], k))
        rr_scores.append(reciprocal_rank(ranked_ids, q["relevant_id"]))

    return {
        "model": model_name,
        "dim": corpus_vectors.shape[1],
        "encode_seconds": round(elapsed, 1),
        "mrr": round(float(np.mean(rr_scores)), 4),
        **{f"recall@{k}": round(float(np.mean(v)), 4) for k, v in recalls.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=str, default=None, help="쉼표로 구분된 HF 모델 이름 목록")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",")] if args.models else DEFAULT_MODELS

    corpus = load_jsonl(EVAL_DIR / "embedding_corpus.jsonl")
    queries = load_jsonl(EVAL_DIR / "embedding_queries.jsonl")
    print(f"코퍼스 {len(corpus)}개, 쿼리 {len(queries)}개로 평가\n")

    results = []
    for model_name in models:
        print(f"--- {model_name} 인코딩 중 (CPU라 시간 좀 걸림) ---")
        result = evaluate_model(model_name, corpus, queries)
        results.append(result)
        print(result, "\n")

    print("=== 요약 ===")
    header = ["model", "dim", "encode_seconds", "mrr"] + [f"recall@{k}" for k in K_VALUES]
    print(" | ".join(header))
    for r in results:
        print(" | ".join(str(r[h]) for h in header))


if __name__ == "__main__":
    main()
