# Codex 지시문 — RAG용 `admin_documents` DB 확장 영향범위 분석

## 0. 목적

현재 MediSense RAG 문서 적재 개선을 위해 `vector_db.admin_documents` 확장을 검토 중이다.

현재 검토 중인 최소 변경안은 다음과 같다.

```text
document_title  VARCHAR(255)
source_type     VARCHAR(30)
cleaned_text    TEXT
metadata        JSONB
content_hash    VARCHAR(64)   # 권장
```

기존 핵심 구조:

```text
vector_db.admin_documents
└─ vector_db.document_chunks
   └─ vector_db.chunk_embeddings
```

이번 작업에서는 **DB나 코드를 수정하지 말고**, 위 컬럼을 실제로 추가할 경우 프로젝트 전체에 어떤 영향이 발생하는지 코드 기준으로 조사한다.

---

## 1. 반드시 확인할 것

### 1.1 DB / ORM / Migration

- `admin_documents` ORM 모델 위치와 실제 컬럼 정의
- Alembic Migration 구조
- 현재 Migration 체인으로 위 컬럼 추가가 안전한지
- 기존 초기 Migration의 빈 `upgrade()` 문제가 이번 변경에 어떤 영향을 주는지
- 기존 행이 있는 상태에서 Nullable 컬럼 추가가 안전한지
- `metadata` DB 컬럼과 SQLAlchemy `Base.metadata` 이름 충돌 가능성
- ORM 속성을 `document_metadata` 등으로 매핑해야 하는지
- `content_hash`에 Index/Unique를 걸 경우 영향
- 기존 FK/Cascade/Transaction 영향

### 1.2 저장 경로

현재 실제 저장 Call Flow를 추적한다.

```text
Admin RAG 탭
→ vector-save
→ admin_ocr
→ embedding_service
→ DocumentRepository
→ admin_documents
→ document_chunks
→ chunk_embeddings
```

새 컬럼을 추가하면 다음 파일/함수 중 무엇을 수정해야 하는지 확인한다.

- Request/Response Schema
- Job 객체
- `admin_ocr`
- `DocumentRepository`
- ORM
- Frontend API 타입
- Admin UI
- Test

### 1.3 기존 데이터 호환성

현재 기존 행에는 새 컬럼이 없으므로 다음을 분석한다.

```text
document_title = NULL
source_type = NULL
cleaned_text = NULL
metadata = NULL
content_hash = NULL
```

상태에서도 기존 검색/RRF/Chat이 정상 동작하는지 확인한다.

특히:

- 기존 `ocr_extracted_text`는 실제로 Clean Text가 들어간 행이 있음
- 새 구조에서는 `ocr_extracted_text = Raw`, `cleaned_text = Clean`으로 의미를 바꾸려 함
- 기존 행을 어떻게 호환해야 하는지
- `COALESCE(cleaned_text, ocr_extracted_text)`가 필요한 위치
- 기존 데이터 Backfill이 필수인지 선택인지

### 1.4 Chunk / Embedding 영향

다음 구조를 그대로 유지 가능한지 확인한다.

```text
document_chunks
chunk_embeddings
jina-v4
medical-bgem3
RRF
```

부모 테이블 확장만으로:

- Chunk 저장
- Jina/BGE Embedding
- pgvector 검색
- RRF
- Chat RAG Context

가 깨지지 않는지 실제 코드 호출 기준으로 확인한다.

### 1.5 검색 결과 Metadata 반환

현재 검색 결과가 `document_chunks` 중심이라면, 새 Metadata를 사용자/관리자 검색 결과에서 쓰기 위해 Parent `admin_documents` Join이 필요한지 확인한다.

다음을 구분한다.

```text
DB 컬럼 추가만 하면 되는 부분
저장 코드 수정이 필요한 부분
검색 Join이 필요한 부분
Frontend 타입/UI 수정이 필요한 부분
```

### 1.6 대용량 경로 영향

20MB 초과 R2/Streaming 경로가 일반 inline 저장과 다르므로 반드시 별도 확인한다.

- `ocr_extracted_text`가 전체 Raw가 아니라 Preview인 현재 구조
- `cleaned_text`를 어떻게 다룰 수 있는지
- `source_type`
- `metadata`
- `content_hash`
- staged multiple commit 구조

이번 최소 구현에서 대용량 경로를 완전 지원하지 않아도 된다면,
어떤 예외 정책을 두는 것이 안전한지 제안한다.

---

## 2. 프로젝트 전체 영향 파일 조사

위 컬럼 추가 시 영향을 받는 파일을 프로젝트 전체에서 검색한다.

특히 다음 키워드 사용:

```text
AdminDocuments
admin_documents
ocr_extracted_text
original_file_url
ocr_status
DocumentRepository
save_with_chunks
vector-save
document_id
RetrievedChunk
RagSearchResultItem
```

최종 결과를 아래 표로 작성한다.

| 파일 | 현재 역할 | DB 확장 영향 | 수정 필요 | 수정 이유 |
|---|---|---|---|---|

상태:

```text
필수 수정
선택 수정
영향 없음
확인 필요
```

---

## 3. 변경안별 영향 비교

다음 두 안을 비교한다.

### A. 최소안

```text
document_title
source_type
cleaned_text
metadata JSONB
```

### B. 권장안

```text
document_title
source_type
cleaned_text
metadata JSONB
content_hash
```

각 안에 대해:

- Migration 난이도
- Backend 수정 범위
- Frontend 수정 범위
- 기존 데이터 영향
- 검색 영향
- 중복 등록 대응
- 예상 위험

을 비교한다.

---

## 4. `metadata JSONB` 내부 구조 제안

현재 약 30개 의료 문서 규모를 기준으로 최소 구조를 제안한다.

후보:

```json
{
  "source_name": "질병관리청",
  "language": "ko",
  "license": "...",
  "category": "질환",
  "topic": "고혈압"
}
```

다음은 이번 기본 구조에 반드시 넣지 않아도 된다.

```text
symptoms
disease
department
red_flag
```

각 필드가 현재 검색이나 저장에서 실제로 사용되는지 코드 기준으로 판단한다.

---

## 5. 절대 하지 말 것

이번 작업은 영향 분석만 수행한다.

```text
DB ALTER 금지
Migration 생성/실행 금지
ORM 수정 금지
소스 수정 금지
Neon 데이터 변경 금지
재임베딩 금지
Git commit/push 금지
```

실 DB 확인이 필요한 사항은 `실DB 확인 필요`라고 기록한다.

---

## 6. 최종 보고서

다음 내용을 포함하는 Markdown 보고서를 작성한다.

```text
1. 현재 admin_documents 구조
2. 제안 DB 확장안
3. 전체 코드 영향 범위
4. 저장 경로 영향
5. 기존 데이터 호환성
6. Chunk/Embedding/RRF 영향
7. 검색/Chat 영향
8. 대용량 경로 영향
9. Migration 위험요소
10. 최소안 vs 권장안 비교
11. 반드시 수정할 파일
12. 수정하지 않아도 되는 파일
13. 팀 협의가 필요한 항목
14. 실제 DB 변경 전 체크리스트
15. 최종 권장안
```

---

## 7. 마지막에 반드시 답할 질문

1. `admin_documents`만 확장하는 것으로 충분한가?
2. `document_chunks`, `chunk_embeddings`는 정말 수정하지 않아도 되는가?
3. 새 컬럼 추가만으로 기존 Jina/BGE/RRF 검색이 깨질 가능성이 있는가?
4. 기존 행의 NULL 값은 문제 없는가?
5. `ocr_extracted_text`의 의미를 Raw로 바꾸면 기존 코드 어디가 영향을 받는가?
6. `cleaned_text`를 새로 추가하면 어떤 코드가 이를 우선 사용해야 하는가?
7. `metadata JSONB`를 추가할 때 ORM 이름 충돌은 어떻게 처리해야 하는가?
8. `content_hash`는 지금 넣는 것이 좋은가, 나중에 넣어도 되는가?
9. Migration 생성 전에 반드시 사람이 확인해야 할 것은 무엇인가?
10. 팀원과 합의가 필요한 DB 변경사항은 정확히 무엇인가?

분석 완료 후 구현하지 말고 사용자 지시를 기다린다.
