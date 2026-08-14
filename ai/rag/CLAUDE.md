# ai/rag — 청킹 · 임베딩 · 검색

## 모델 (2026-08 기준 선정 — 근거는 Bruno 가이드 옆 대화 기록/PR 설명 참고)
| 역할 | 모델 | 비고 |
|---|---|---|
| 의미기반 임베딩 | `dragonkue/snowflake-arctic-embed-l-v2.0-ko` | **1024차원** — `vector_db.document_chunks.embedding`(VECTOR(1024))과 반드시 일치해야 함. 한국어 검색 벤치마크 8종 평균 최상위권, Apache-2.0 |
| 키워드기반 검색 | Kiwi(형태소 분석) + Tantivy(Rust 풀텍스트 엔진) | 신경망 아님 — GPU/추론 비용 없음. SPLADE 같은 sparse 신경망 모델은 별도 인덱스 인프라(Elasticsearch류)가 필요해서 안 씀 |
| 결합 | RRF (Reciprocal Rank Fusion) | 점수가 아니라 순위만 쓰기 때문에 dense/keyword 두 방식의 점수 스케일이 달라도 한쪽이 지배하지 않음 |
| 재정렬(옵션) | `dragonkue/bge-reranker-v2-m3-ko` | cross-encoder라 후보 하나하나 다시 추론 — 제일 비쌈. `pipeline.retrieve(..., use_reranker=)`로 토글. 리소스 제약 배포 환경(무료 티어)에서는 끄는 걸 권장 |

**임베딩 모델을 바꾸려면 DB 마이그레이션이 같이 필요하다** (`vector_db.document_chunks.embedding`
차원 변경) — 가볍게 교체하지 말 것.

## 모듈
- `chunking.py` — 문장 경계 기준으로, 글자 수가 아니라 임베딩 모델과 같은 토크나이저로 잰
  **토큰 수**로 자른다(`max_tokens` 기본 300). 앞 청크 끝부분을 다음 청크 앞에 토큰
  단위로 겹치고(`overlap_tokens` 기본 60), 문장부호 없이 예산을 넘는 덩어리는 토큰
  단위로 강제 분할한다. 공백/기호뿐인 의미 없는 청크는 `is_garbage()`로 걸러서 버린다.
- `embedding.py` — `embed_texts`/`embed_query`. 모델은 `_get_model()`에서 지연 로딩+캐싱.
  `normalize_embeddings=True`로 뽑기 때문에 코사인 유사도가 내적(dot product)과 같다.
- `keyword_search.py` — `search(chunks, query, top_k)`. 호출마다 임시 Tantivy 인덱스를
  새로 만든다(문서 단위 청크 수가 적어서 충분히 빠름, 상태를 안 들고 있어도 됨).
- `hybrid.py` — `reciprocal_rank_fusion(ranked_lists, k=60)`.
- `reranker.py` — `rerank(query, candidates)`. 모델은 마찬가지로 지연 로딩+캐싱.
- `pipeline.py` — 위 전부를 묶은 `retrieve(chunks, query, top_k, use_reranker)`. 실제
  호출은 대부분 이 함수 하나만 쓰면 된다.

## 절대 금지 (루트 CLAUDE.md에서 이어짐)
- **검색되지 않은 내용을 RAG 근거처럼 생성 금지** — `retrieve()`가 반환한 `RetrievedChunk`
  이외의 텍스트를 "근거 문서"라고 LLM 프롬프트에 끼워넣지 말 것.
- Train-Test 데이터 누수 금지 — 나중에 리랭커/임베딩을 파인튜닝하게 되면 평가셋과
  학습셋이 겹치지 않도록 각별히 주의.

## 재사용
`backend/local_lab`(로컬 성능테스트)과 향후 `ai/consultation`(증상 상담 RAG)이 이 패키지를
그대로 호출한다.
