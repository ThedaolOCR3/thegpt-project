"""문장 임베딩 — dragonkue/snowflake-arctic-embed-l-v2.0-ko (1024차원, 한국어 검색
벤치마크 상위권, Apache-2.0). DB의 vector_db.document_chunks.embedding이
VECTOR(1024)라 이 모델과 차원이 맞아야 한다 — 다른 임베딩 모델로 바꾸려면 스키마도
같이 바뀌어야 함을 유의."""
from functools import lru_cache

import numpy as np

EMBEDDING_MODEL_NAME = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"
EMBEDDING_DIM = 1024


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    # normalize_embeddings=True: 벡터를 단위벡터로 만들어, 내적만으로 코사인 유사도가 나오게 한다.
    vectors = model.encode(texts, normalize_embeddings=True)
    return np.asarray(vectors).tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
