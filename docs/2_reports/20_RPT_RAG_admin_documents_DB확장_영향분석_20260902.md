# RAG `admin_documents` DB 확장 영향 분석

> 문서 유형: 사전 영향 분석 보고서  
> 작성일: 2026-09-02  
> 분석 기준 브랜치: `test/merge-fix`  
> 분석 기준 커밋: `91569984376b39b84738161484c60d981dad4719`  
> 대상: `vector_db.admin_documents` 확장안 A/B  
> 작업 제한: 코드·DB·Migration·ORM 수정, Neon 반영, 재임베딩, 커밋 미실시

---

## 1. 결론 요약

현재 목표가 약 30건 규모의 정제 문서를 RAG에 적재하고 출처·분류 정보를 보존하는 것이라면, **기존 `admin_documents`를 확장하는 방식으로 충분하다.** 별도 문서 마스터 테이블을 지금 추가할 필요는 없다.

권고안은 **B안**이다.

```text
document_title VARCHAR(255) NULL
source_type    VARCHAR(30)  NULL
cleaned_text   TEXT         NULL
metadata       JSONB        NULL
content_hash   VARCHAR(64)  NULL
```

다만 다음 조건을 함께 적용해야 한다.

1. 첫 Migration에서는 기존 행과 구버전 애플리케이션 호환을 위해 모든 신규 컬럼을 nullable로 둔다.
2. `metadata`는 실제 DB 컬럼명으로 유지하되 SQLAlchemy 속성명은 `document_metadata`처럼 분리한다.
3. `content_hash`는 정규화가 끝난 전체 `cleaned_text`의 UTF-8 SHA-256으로 정의하고, 초기에는 비고유 인덱스만 둔다.
4. 기존 `document_chunks`와 `chunk_embeddings`의 컬럼·벡터 차원·제약조건은 변경하지 않는다.
5. 기존 행의 검색 및 문서 단위 조회에는 필요 시 `COALESCE(cleaned_text, ocr_extracted_text)` 호환 규칙을 사용한다.
6. 20MB 초과 대용량 문서는 현재 전체 정제문이 아니라 미리보기와 R2 청크 아티팩트만 보존하므로, 전체 정제·해시 계약이 구현되기 전에는 `cleaned_text`와 `content_hash`를 NULL로 두는 것이 안전하다.
7. 실제 Migration 실행 전 Neon 대상 브랜치, 실스키마, Alembic revision, 기존 데이터와 중복 현황은 반드시 별도 확인한다. **실DB 확인 필요**.

이 확장만으로 Jina/BGE 임베딩이나 RRF 계산은 깨지지 않는다. 현재 검색은 `document_chunks.chunk_text`와 `chunk_embeddings.embedding`을 사용하며, 신규 부모 컬럼을 점수 계산에 사용하지 않기 때문이다.

---

## 2. 분석 범위와 제외 범위

### 2.1 분석 범위

- `vector_db.admin_documents` ORM 및 Migration 영향
- OCR 파일/URL 저장 경로
- 20MB 초과 대용량 문서 staged 저장 경로
- 문서 청크, Jina/BGE 임베딩, 하이브리드 검색과 RRF 영향
- RAG 검색 API, 검색 화면, 상담 Chat 컨텍스트 영향
- 기존 행의 NULL 호환성
- Raw/Clean 텍스트 의미 변경 영향
- JSONB ORM 매핑과 `content_hash` 정책
- 수정 필요 파일과 수정 불필요 파일
- 팀 합의 사항과 Migration 전 체크리스트

### 2.2 제외 범위

- 코드 수정
- ORM 파일 수정 또는 재생성
- Alembic Migration 생성·적용
- Neon DB 접속 또는 스키마 변경
- 기존 문서 backfill
- 기존 청크 재생성 및 재임베딩
- Git 커밋

따라서 이 보고서의 실DB 관련 판단은 코드 저장소 기준의 사전 분석이며, 실환경 사실로 확정하지 않는다.

---

## 3. 현재 `admin_documents` 구조

코드 기준 ORM은 `backend/app/models/generated.py`의 `AdminDocuments`이며, 테이블은 `vector_db.admin_documents`이다.

| 컬럼 | 코드 기준 타입 | nullable | 기본값/관계 | 현재 의미 |
|---|---|---:|---|---|
| `id` | UUID | 아니오 | PK, `gen_random_uuid()` | 문서 ID |
| `original_file_url` | VARCHAR(500) | 아니오 | - | 원본 URL, R2 참조 또는 내부 식별 URL |
| `uploaded_by` | UUID | 예 | `app_db.users.id` FK | 업로더 |
| `ocr_extracted_text` | TEXT | 예 | - | 현재 저장 경로에서는 사실상 정제된 OCR 결과 또는 대용량 미리보기 |
| `ocr_status` | VARCHAR(20) | 예 | `pending` | 처리 상태 |
| `created_at` | TIMESTAMPTZ | 예 | `now()` | 생성 시각 |

관련 자식 테이블은 다음과 같다.

| 테이블 | 핵심 관계/구조 | 현재 역할 |
|---|---|---|
| `vector_db.document_chunks` | `document_id` → `admin_documents.id`, `ON DELETE CASCADE` | 검색·임베딩 대상 청크 본문 보존 |
| `vector_db.chunk_embeddings` | `chunk_id` → `document_chunks.id`, `ON DELETE CASCADE`, `(chunk_id, provider_name)` unique | 공급자별 벡터 보존 |

코드의 Migration 체인은 `5d7e62474617` → `2e7a98381f96` → `03b8a4b5b62a` → `0dcef89659d1` 순서다. 다만 최초 Migration의 `upgrade()`/`downgrade()`가 비어 있고, 후속 Migration은 기존 스키마가 이미 있다고 가정한다. 그러므로 저장소의 Migration만 보고 빈 DB를 완전히 재구성할 수 있다고 판단하면 안 된다.

**실DB 확인 필요:** 실제 Neon의 테이블 컬럼, 타입, default, nullable, FK, index, `alembic_version`이 코드와 동일한지 확인해야 한다.

---

## 4. 제안 확장안

### 4.1 A안: 최소 확장

```sql
document_title VARCHAR(255) NULL,
source_type    VARCHAR(30)  NULL,
cleaned_text   TEXT         NULL,
metadata       JSONB        NULL
```

역할은 다음과 같다.

| 컬럼 | 역할 | 저장 주체 |
|---|---|---|
| `document_title` | 사용자에게 표시할 문서 제목 | OCR 작업 결과의 파일명/문서명 또는 관리자 입력 |
| `source_type` | 문서 유입 유형 | 백엔드가 `file`/`url` 등 통제값으로 저장 |
| `cleaned_text` | 정제 완료된 문서 단위 텍스트 | OCR 정제 파이프라인 |
| `metadata` | 출처·언어·라이선스·분류 확장 정보 | 백엔드 검증 후 저장 |

### 4.2 B안: 권고 확장

A안에 다음을 추가한다.

```sql
content_hash VARCHAR(64) NULL
```

`content_hash`는 동일한 정제 문서의 중복 후보를 빠르게 찾기 위한 값이다. 권장 계약은 다음과 같다.

- 대상: **최종 전체 `cleaned_text`**
- 인코딩: UTF-8
- 알고리즘: SHA-256
- 저장 형식: 64자리 소문자 hexadecimal
- 계산 위치: 프론트엔드가 아닌 백엔드
- 초기 제약: nullable, 비고유 B-tree index
- 초기 동작: 중복 차단보다 중복 후보 탐지·경고

파일 바이트 해시는 같은 문서의 포맷 차이로 달라지고, 과도한 공백 정규화는 의학 문서 의미를 바꿀 수 있다. 따라서 해시 계산 전 정규화 규칙과 정제기 버전을 팀이 고정해야 한다.

---

## 5. A안과 B안 비교

| 항목 | A안 | B안 |
|---|---|---|
| 신규 컬럼 | 4개 | 5개 |
| Migration 난이도 | 낮음: nullable 컬럼 4개 | 낮음~중간: nullable 컬럼 5개와 index |
| 백엔드 수정 범위 | 제목·유형·Raw/Clean·metadata 저장 | A안 범위 + 해시 계산·중복 후보 처리 |
| 프론트 수정 범위 | 자동 metadata만 쓰면 없음, 관리자 입력 시 타입/UI 필요 | A안과 동일, 중복 경고 UX를 제공하면 추가 수정 |
| 기존 데이터 영향 | 신규 값 NULL, fallback 필요 | 신규 값 NULL, hash 미생성 행은 중복 검사 제외 |
| 검색 영향 | 저장만 하면 없음, 노출/필터 시 join 필요 | A안과 동일 |
| 출처/분류 보존 | 가능 | 가능 |
| Raw/Clean 분리 | 가능 | 가능 |
| 정확 중복 후보 탐지 | 별도 전체 비교 필요 | 해시 조회로 가능 |
| 추가 구현 | 기본 저장·조회 | 해시 계약, 계산, 조회, 테스트 추가 |
| 예상 위험 | Raw/Clean 혼재, JSONB 규칙 부재 | A안 위험 + 잘못된 unique/해시 계약 위험 |
| 고유 제약 위험 | 없음 | 초기 unique 적용 시 중복/운영 정책 충돌 가능 |
| 30건 초기 운영 | 가능 | 더 적합 |
| 장기 확장성 | 보통 | 좋음 |

**권고:** 어차피 스키마 Migration을 한 번 수행해야 하므로 B안을 채택하되, `content_hash`에 곧바로 unique 제약을 걸지 않는다. 컬럼 추가의 한계비용은 작고, 이후 문서 증가 시 중복 탐지 기반이 된다.

---

## 6. 저장 경로 영향 분석

### 6.1 현재 일반 파일/URL 경로

현재 흐름은 다음과 같다.

```text
프론트 OCR 요청
  → OCR/웹 추출
  → 정제된 텍스트로 청크 생성
  → 완료된 OCR Job 보관
  → 프론트가 jobId만 저장 API로 전송
  → 문서 행 생성
  → 청크 생성
  → Jina/BGE 임베딩 생성·저장
  → 단일 트랜잭션 commit
```

현재 `OcrDocumentResponse.extracted_text`에는 `result.cleaned_text`가 들어간다. 이후 저장 API는 `job.result.extracted_text`를 `DocumentRepository.save_with_chunks(... extracted_text=...)`에 넘기고, 저장소는 이를 `admin_documents.ocr_extracted_text`에 기록한다.

즉 현재 `ocr_extracted_text`라는 이름과 달리 실제 일반 저장값은 이미 **정제 텍스트**다. Raw/Clean 의미를 명확히 바꾸려면 단순 컬럼 추가만으로 끝나지 않는다.

### 6.2 신규 컬럼별 일반 저장 영향

| 신규 컬럼 | 현재 데이터로 자동 저장 가능 | 필요한 변경 |
|---|---:|---|
| `document_title` | 예 | Job의 `document_name`을 저장소까지 전달 |
| `source_type` | 예 | Job의 `source_type`을 통제값으로 전달 |
| `cleaned_text` | 예 | 현재 `extracted_text` 값을 명시적 `cleaned_text`로 전달 |
| `metadata` | 일부 | 시스템 생성값은 가능, 관리자 입력값은 요청 DTO/UI 필요 |
| `content_hash` | 예 | 백엔드에서 최종 `cleaned_text`로 계산 |
| Raw용 `ocr_extracted_text` | 아니오 | Job 결과가 Raw 텍스트도 별도로 보존하도록 변경 필요 |

`document_title`, `source_type`, `cleaned_text`, 자동 생성 metadata만 저장한다면 프론트 요청은 계속 `jobId` 하나만 보낼 수 있다. 반면 관리자가 `source_name`, `license`, `category`, `topic`을 지정해야 한다면 저장 요청 스키마와 프론트 상태/UI가 필요하다.

### 6.3 저장소 인터페이스 권고

현재의 모호한 `extracted_text` 인자는 의미를 분리해야 한다.

```text
raw_text
cleaned_text
document_title
source_type
document_metadata
content_hash
```

이름을 분리하지 않으면 호출자가 Raw를 전달했는지 Clean을 전달했는지 검증할 수 없다. 단, 실제 구현 시 한 번에 시그니처를 바꾸면 테스트용 fake repository도 함께 수정해야 한다.

### 6.4 트랜잭션 영향

일반 파일/URL 경로는 부모 문서, 청크, 임베딩을 한 트랜잭션으로 commit한다. 신규 컬럼이 nullable이면 기존 원자성은 유지된다. `content_hash` unique를 바로 적용하면 동시 저장 시 `IntegrityError` 처리와 사용자 응답 정책이 추가로 필요하므로 초기에는 권장하지 않는다.

---

## 7. Raw/Clean 의미 변경 영향

### 7.1 권장 의미

| 필드 | 권장 의미 |
|---|---|
| `ocr_extracted_text` | OCR/웹 추출 직후의 Raw 텍스트 |
| `cleaned_text` | RAG 청킹에 사용한 최종 정제 텍스트 |
| `document_chunks.chunk_text` | `cleaned_text`에서 만들어진 검색 단위 텍스트 |

### 7.2 현재와의 차이

- 일반 파일/URL: 현재 `ocr_extracted_text`에는 Clean이 저장된다.
- 대용량 파일: 현재 `ocr_extracted_text`에는 전체 텍스트가 아닌 최대 100,000자의 미리보기가 저장된다.
- 온라인 RAG 검색: 부모의 `ocr_extracted_text`를 읽지 않고 `document_chunks.chunk_text`를 읽는다.

따라서 앞으로 `ocr_extracted_text`를 Raw로 저장해도 현재 Jina/BGE/RRF 검색 결과는 직접 변하지 않는다. 하지만 다음 경계에서는 의미 변경을 반영해야 한다.

- OCR Job 내부 결과가 Raw와 Clean을 각각 보존하는 지점
- 저장 서비스와 repository 인자명
- 문서 미리보기·내보내기·재처리 기능
- 기존 행 backfill 또는 호환 조회
- 운영 문서와 데이터 사전
- 대용량 문서의 “전체 원문”과 “미리보기” 구분

기존 행은 `ocr_extracted_text`가 Clean인 상태이므로 일괄적으로 Raw라고 재해석하면 안 된다. 별도 backfill이 없다면 기존/신규 행의 의미가 혼재한다. 최소한 metadata 또는 명시적 처리 버전으로 의미를 구분하거나, 과거 행은 legacy clean으로 문서화해야 한다.

---

## 8. `cleaned_text` 우선 사용 위치

`cleaned_text`는 다음 지점에서 우선 사용해야 한다.

1. 청크 생성 입력
2. 임베딩 입력의 원천
3. `content_hash` 계산
4. 문서 단위 미리보기·내보내기
5. 문서 재청킹·재임베딩 입력
6. 과거 데이터 호환이 필요한 문서 단위 조회

기존 행 호환용 문서 단위 표현은 다음 개념을 사용한다.

```sql
COALESCE(cleaned_text, ocr_extracted_text)
```

다만 현재 검색 결과 본문은 이미 `document_chunks.chunk_text`에서 나오므로 검색 쿼리에 위 표현을 무조건 추가할 필요는 없다. 부모 전체 텍스트를 청크 검색마다 읽으면 불필요한 I/O만 증가한다.

---

## 9. 대용량 문서 경로 영향

### 9.1 현재 경로의 특성

20MB 초과 대용량 Text/ZIP 경로는 일반 경로와 구조가 다르다.

```text
대용량 파일
  → 스트리밍 고정 문자 청킹
  → 전체 청크를 R2 아티팩트에 저장
  → 최대 100,000자 preview_text와 최초 20개 preview_chunks만 Job에 유지
  → 부모 문서를 먼저 commit
  → 임베딩을 batch 단위로 append/commit
  → 완료 상태로 전환
  → 실패 시 보상 삭제
```

현재 대용량 `extracted_text`는 전체 Raw도 전체 Clean도 아닌 미리보기다. 이를 그대로 신규 `cleaned_text`에 저장하면 “전체 정제 텍스트”라는 데이터 계약을 위반한다.

### 9.2 초기 안전안

- `document_title`: 저장 가능
- `source_type`: 원본 유입 기준 `file`로 저장
- `metadata`: 저장 가능하며 `storage_mode: r2`, `text_truncated: true`, `cleaning_status: not_applied` 같은 시스템 상태를 포함할 수 있음
- `cleaned_text`: 전체 정제 스트리밍 경로가 생기기 전까지 NULL 권고
- `content_hash`: 전체 정제 텍스트의 streaming hash가 없으면 NULL 권고
- `ocr_extracted_text`: preview를 저장한다면 `text_scope=preview`를 metadata로 명확히 표시

`source_type`에 `r2`를 넣는 것은 권장하지 않는다. `file`/`url`은 유입 유형이고 R2는 저장 방식이므로 서로 다른 차원이다.

### 9.3 staged transaction 영향

부모 행이 먼저 commit되고 이후 청크가 여러 차례 commit되므로, 향후 신규 컬럼을 NOT NULL로 만들면 `begin_staged_save()`가 첫 commit 전에 모든 필수값을 제공해야 한다. 첫 Migration을 nullable로 두면 기존 staged 흐름은 유지된다.

---

## 10. 기존 데이터 호환성

### 10.1 신규 nullable 컬럼

기존 행에 신규 컬럼이 NULL이어도 현재 검색·대시보드·사용자 탈퇴 처리에는 직접 문제가 없다.

- 검색은 `document_chunks`와 `chunk_embeddings` 중심이다.
- 대시보드는 문서 ID를 count한다.
- 사용자 삭제 경로는 `uploaded_by`를 NULL로 갱신한다.
- 신규 부모 컬럼은 현재 코드에서 참조하지 않는다.

### 10.2 NULL fallback 규칙

| 값 | 권장 fallback |
|---|---|
| 표시 제목 | 파일명 추출 또는 `문서 {id}` |
| 출처 | `original_file_url`, 없으면 `출처 미상` |
| `metadata` | 애플리케이션에서 빈 객체로 취급 |
| 문서 단위 clean 본문 | `COALESCE(cleaned_text, ocr_extracted_text)` |
| `content_hash` | NULL이면 중복 검사 미대상 |

### 10.3 backfill 필요성

초기 호환 운영에는 backfill이 필수가 아니다. 다음을 도입할 때는 필요하다.

- 신규 컬럼 NOT NULL 전환
- 전체 데이터에 대한 중복 탐지 보장
- `content_hash` unique/부분 unique 제약
- metadata 기반 필터가 모든 문서에 적용되어야 하는 요구
- Raw/Clean 의미를 모든 행에서 일관되게 보장해야 하는 요구

기존 `ocr_extracted_text`를 `cleaned_text`로 복사하는 backfill은 가능하지만, 대용량 행은 미리보기일 수 있으므로 일괄 복사 전에 행 유형을 구분해야 한다. **실DB 확인 필요**.

---

## 11. JSONB `metadata` 설계와 ORM 충돌

### 11.1 최소 권장 구조

```json
{
  "source_name": "질병관리청",
  "language": "ko",
  "license": "공공누리 제1유형",
  "category": "질환",
  "topic": "고혈압"
}
```

초기 필수 검토 키는 다음 다섯 개면 충분하다.

- `source_name`
- `language`
- `license`
- `category`
- `topic`

`document_title`과 `source_type`은 정규 컬럼이 있으므로 JSONB에 중복 저장하지 않는다. 증상, 질환, 진료과, red flag 등 세부 의료 태그는 검색·필터 요구와 용어 체계가 합의된 뒤 확장한다.

### 11.2 SQLAlchemy 이름 충돌

SQLAlchemy declarative base에는 이미 `metadata`라는 예약 성격의 속성이 있다. DB 컬럼명이 `metadata`여도 Python ORM 속성명을 그대로 `metadata`로 선언하면 충돌할 수 있다.

권장 매핑 개념은 다음과 같다.

```python
document_metadata = mapped_column("metadata", JSONB, nullable=True)
```

실제 구현 시 `generated.py`가 sqlacodegen으로 생성되는 파일이라는 점도 고려해야 한다. DB 변경 후 재생성 결과가 안전한 속성명을 만드는지 확인하고, 생성기가 충돌명을 안정적으로 처리하지 못하면 생성 후 보정 정책 또는 별도 수동 모델 정책을 팀이 결정해야 한다.

### 11.3 JSONB 검증

프론트에서 임의 JSON 객체를 그대로 받는 방식은 권장하지 않는다. Pydantic 요청 모델에서 허용 키, 문자열 길이, nullable, 통제어를 검증하고 DB에는 검증된 dict만 저장해야 한다. Python 모델의 mutable 기본값 `{}`도 피하고 `default_factory`를 사용한다.

DB default를 `'{}'::jsonb`로 둘지는 팀 선택이다. 초기에는 컬럼 NULL + 애플리케이션 fallback이 Migration 부담이 가장 작다.

---

## 12. `content_hash` 도입 정책

### 12.1 지금 도입할 이유

- 초기 30건부터 동일 자료의 재업로드를 탐지할 수 있다.
- 차후 문서 수 증가 후 전체 해시 backfill을 하는 것보다 비용이 작다.
- 신규 Migration에 한 컬럼과 인덱스를 함께 포함할 수 있다.
- 청크/임베딩을 만들기 전 중복 후보를 확인하면 외부 임베딩 호출을 줄일 수 있다.

### 12.2 지금 unique를 권하지 않는 이유

- 같은 내용이 서로 다른 공식 출처에서 제공될 수 있다.
- 같은 문서를 버전 또는 라이선스 이력 보존 목적으로 다시 저장할 수 있다.
- 정제 규칙이 바뀌면 의미상 같은 문서의 해시가 달라질 수 있다.
- 기존 중복 데이터 유무를 아직 확인하지 않았다.
- 동시 저장 충돌에 대한 API·UI 정책이 없다.

따라서 초기에는 비고유 index와 서비스 레벨의 탐지·경고가 적절하다. 글로벌 중복 금지가 확정되면 실데이터 조사와 backfill 후 `WHERE content_hash IS NOT NULL` 부분 unique 또는 출처/버전을 포함한 복합 정책을 검토한다. **실DB 확인 필요**.

---

## 13. `document_chunks`·`chunk_embeddings`·RRF 영향

### 13.1 스키마 변경 필요성

이번 목적만으로는 두 자식 테이블을 변경할 필요가 없다.

- `document_chunks`는 이미 문서 FK와 검색 본문을 갖는다.
- `chunk_embeddings`는 공급자별 임베딩, 차원, unique 제약을 갖는다.
- 부모 문서 컬럼 추가는 FK 대상 PK를 변경하지 않는다.
- 기존 cascade 삭제 관계도 변하지 않는다.

### 13.2 Jina/BGE 영향

임베딩 입력은 청크 텍스트이고, 공급자 호출 및 벡터 저장은 신규 부모 컬럼을 참조하지 않는다. 따라서 nullable 부모 컬럼을 추가하는 것만으로 다음이 변하지 않는다.

- Jina embedding 모델 호출
- BGE embedding 모델 호출
- 벡터 차원
- provider별 저장 구조
- 기존 임베딩 값
- 재임베딩 필요성

### 13.3 RRF 영향

RRF는 공급자별 검색 순위/점수를 결합한다. `document_title`, `source_type`, `cleaned_text`, `metadata`, `content_hash`는 현재 후보 생성이나 결합식에 들어가지 않으므로 점수 계산은 동일하다.

향후 metadata 필터를 적용한다면 필터는 각 공급자 후보 조회에 동일하게 적용해야 한다. 한 공급자 쿼리에만 필터를 적용하면 RRF 입력 집합이 비대칭이 되어 결과 해석이 어려워진다.

---

## 14. 검색 API 및 Chat 영향

### 14.1 현재 검색 경로

`DocumentChunkRepository.search_by_provider()`는 `AdminDocuments`를 join하지만 현재 목적은 `ocr_status == completed` 필터다. 반환값은 청크와 distance이며, 부모의 제목·출처·metadata는 결과 DTO에 싣지 않는다.

`RagSearchResultItem`도 현재 `chunk_id`, `document_id`, `content`, `score`만 제공한다. 반면 프론트 `RagSearchResult` 타입에는 이미 optional `source`, `metadata`가 있어 백엔드 응답과 표현력이 어긋나 있다.

### 14.2 신규 metadata를 검색 결과에 사용하는 경우

다음 변경이 필요하다.

1. 기존 join에서 부모 제목·URL·metadata를 함께 projection한다.
2. `RetrievedChunk.source`와 `RetrievedChunk.metadata`를 채운다.
3. `RagSearchResultItem`과 router 응답에 optional 필드를 추가한다.
4. NULL 행에는 fallback을 적용한다.
5. N+1 문서 조회가 생기지 않도록 기존 검색 쿼리에서 함께 가져온다.

프론트는 optional 필드를 이미 받을 수 있으나 실제 표시 요구가 있다면 metadata UI와 타입 구체화가 추가로 필요하다.

### 14.3 Chat 경로

상담 Chat은 RAG 검색 결과의 청크를 컨텍스트로 사용한다. 현재 consultation context는 optional `source`를 처리할 수 있으므로, 검색 서비스가 출처를 채우면 Chat 근거 출처도 자연스럽게 개선된다.

metadata 자체는 현재 프롬프트 구성이나 점수 계산에 사용되지 않는다. 의료 답변의 동작을 바꾸려면 별도의 사용 정책, 예를 들어 공식 출처 우선, 언어 필터, 카테고리 필터가 필요하다. 단순 저장만으로 Chat 품질이 자동 개선되는 것은 아니다.

---

## 15. 전체 코드 영향도

### 15.1 프로젝트 전체 영향 파일표

상태는 지시문의 분류인 `필수 수정`, `선택 수정`, `영향 없음`, `확인 필요`로 표시했다. `선택 수정`은 DB 컬럼을 단순 저장하는 범위를 넘어 관리자 입력 또는 검색 결과 노출까지 수행할 때 필요하다는 뜻이다.

| 파일 | 현재 역할 | DB 확장 영향 | 수정 필요 | 수정 이유 |
|---|---|---|---|---|
| `backend/app/models/generated.py` | `AdminDocuments`, `DocumentChunks`, `ChunkEmbeddings` ORM | 부모 신규 컬럼 매핑, JSONB 별칭 필요 | 필수 수정 | 애플리케이션이 신규 컬럼을 읽고 쓰려면 ORM 반영 필요 |
| `backend/migrations/versions/<new_revision>.py` | Alembic 증분 DDL | nullable 컬럼 5개와 hash index 추가 | 필수 수정 | 기존 Migration을 고치지 않고 새 revision으로 확장해야 함 |
| `backend/migrations/env.py` | Alembic `target_metadata` 설정 | 생성 모델 Base에 의존 | 확인 필요 | 수정 가능성은 낮지만 autogenerate 절차를 검증해야 함 |
| `backend/scripts/generate_models.py` | 실DB에서 ORM 재생성 | 신규 DB 컬럼 반영 시 generated 파일 덮어씀 | 확인 필요 | 실행 순서와 `metadata` 충돌 처리 결과 확인 필요, 스크립트 자체 수정은 보통 불필요 |
| `backend/app/schemas/admin.py` | OCR Job·저장 Request/Response DTO | Raw/Clean 분리, metadata 입력 계약 | 필수 수정 | 현재 Job과 저장 요청에 필요한 신규 데이터 계약이 없음 |
| `backend/app/services/ocr_workflow.py` | OCR/웹 추출, 정제, 청크 생성, Job 결과 구성 | Raw와 Clean을 각각 보존해야 함 | 필수 수정 | 현재 응답의 `extracted_text`는 Clean만 전달 |
| `backend/app/api/admin/router.py` | `/ocr/vector-save` endpoint | 확장 요청 DTO를 수신 | 영향 없음 | Pydantic DTO가 확장되어도 router가 그대로 service에 전달하므로 직접 로직 변경은 불필요 |
| `backend/app/services/admin_ocr.py` | Job 검증, 임베딩 호출, 저장 orchestration | 제목·유형·Raw·Clean·metadata·hash 전달 | 필수 수정 | 현재 `jobId`로 얻은 Clean을 단일 extracted text로만 저장 |
| `backend/app/repositories/document_repository.py` | 부모/청크/임베딩 일반·staged 저장 | 신규 부모 컬럼 insert와 명시적 인자 필요 | 필수 수정 | 실제 DB write 경계 |
| `backend/app/services/large_document_service.py` | 20MB 초과 스트리밍 청크와 R2 아티팩트 | preview/전체 Clean/hash 예외 정책 필요 | 필수 수정 | 현재 전체 텍스트 대신 preview만 Job에 유지 |
| `backend/app/services/embedding_service.py` | 공급자별 청크 임베딩 | 부모 신규 컬럼 미사용 | 영향 없음 | 입력 청크와 출력 벡터 계약 불변 |
| `backend/app/ai/rag/embeddings/remote.py` | Jina/BGE 원격 임베딩 호출 | 부모 신규 컬럼 미사용 | 영향 없음 | 모델 호출·차원·본문 입력 불변 |
| `backend/app/repositories/document_chunk.py` | provider별 pgvector 검색, 완료 문서 join | 부모 metadata를 반환하려면 projection 확대 | 선택 수정 | 컬럼 저장만으로는 불필요, 검색 결과 노출/필터에는 필요 |
| `backend/app/services/rag_search_service.py` | 공급자 결과 RRF 결합, `RetrievedChunk` 생성 | source/metadata 매핑 가능 | 선택 수정 | 신규 부모 정보를 검색 결과에 싣는 경우 필요 |
| `backend/app/ai/rag/hybrid.py` | 공급자별 결과 RRF 결합 | 신규 컬럼 미사용 | 영향 없음 | 결합 알고리즘과 입력 점수 불변 |
| `backend/app/schemas/rag.py` | RAG 검색 API 응답 DTO | source/metadata optional 필드 필요 | 선택 수정 | 검색 결과에 신규 정보를 반환할 때 필요 |
| `backend/app/api/rag/router.py` | 검색 결과를 API DTO로 변환 | 확장 필드 매핑 필요 | 선택 수정 | source/metadata 응답 시 필요 |
| `backend/app/services/message.py` | Chat에서 RAG 청크 조회 | 확장 `RetrievedChunk`를 그대로 소비 가능 | 영향 없음 | 현재 청크 검색 호출 계약이 유지됨 |
| `backend/app/ai/consultation/context.py` | 상담 프롬프트용 청크 컨텍스트 | optional source는 이미 수용 | 영향 없음 | metadata를 프롬프트에 직접 쓰지 않는 한 변경 불필요 |
| `backend/app/services/dashboard_service.py` | 관리자 문서 count | 신규 컬럼 미사용 | 영향 없음 | 문서 ID count만 수행 |
| `backend/app/repositories/mypage.py` | 사용자 탈퇴 시 `uploaded_by` 정리 | 신규 컬럼 미사용 | 영향 없음 | 기존 nullable FK만 갱신 |
| `backend/app/services/document_ingestion_service.py` | 전달받은 텍스트 청킹·임베딩 보조 | 부모 문서 컬럼 직접 조회 없음 | 영향 없음 | 현 호출 계약에서는 신규 필드 미사용 |
| `frontend/src/features/admin/types/ocr.ts` | OCR/저장 API 타입 | 관리자 metadata 입력 시 payload 확장 | 선택 수정 | 자동 저장만 하면 `jobId` 유지 가능, 사용자 입력 시 필요 |
| `frontend/src/features/admin/services/apiAdminAiService.ts` | vector-save API 호출 | 확장 payload 전달 가능 | 선택 수정 | 관리자 입력 metadata를 보내는 경우 필요 |
| `frontend/src/features/admin/hooks/useOcrTest.ts` | OCR 상태와 저장 동작 관리 | 입력값을 save request에 연결 | 선택 수정 | 현재 저장 시 `jobId`만 전달 |
| `frontend/src/features/admin/components/ocr/OcrPanel.tsx` | Admin OCR 화면 | metadata·제목 입력 UI 가능 | 선택 수정 | 자동 생성값만 저장하면 불필요 |
| `frontend/src/features/admin/components/ocr/OcrResultSummary.tsx` | 정제 결과 preview 표시 | Raw/Clean/metadata 표시 요구 가능 | 선택 수정 | DB 저장 자체에는 영향 없음 |
| `frontend/src/api/rag.ts` | RAG API 타입·호출 | source/metadata가 이미 optional | 영향 없음 | 백엔드가 optional 값을 반환해도 기존 타입이 수용 가능 |
| `backend/tests/test_ocr_workflow.py` | OCR workflow 회귀 테스트 | Raw/Clean 계약 검증 필요 | 필수 수정 | Job 결과 의미가 달라짐 |
| `backend/tests/test_ocr_vector_save.py` | 일반/URL 저장과 API 테스트 | 신규 부모값·hash·NULL 검증 필요 | 필수 수정 | fake repository 시그니처도 함께 영향 |
| `backend/tests/test_large_ocr_vector_save.py` | staged 대용량 저장 테스트 | preview/NULL/hash 예외 검증 필요 | 필수 수정 | `begin_staged_save` 인자와 정책 변경 |
| `backend/tests/test_rag_search_service.py` | RRF 검색 서비스 테스트 | source/metadata 반환 시 fixture 확장 | 선택 수정 | DB 컬럼 저장만 수행하면 기존 테스트 유지 가능 |

### 15.2 반드시 수정해야 하는 파일

아래는 B안과 Raw/Clean 분리를 실제 구현한다는 전제의 최소 필수 범위다.

| 파일/영역 | 변경 이유 |
|---|---|
| `backend/migrations/versions/<new_revision>_extend_admin_documents.py` | 신규 컬럼과 `content_hash` index 추가 |
| `backend/app/models/generated.py` | 신규 DB 컬럼 ORM 반영 및 `metadata` 속성명 충돌 회피 |
| `backend/app/schemas/admin.py` | Job 내부 Raw/Clean 보존, metadata 입력/검증, 필요 시 저장 응답 확장 |
| `backend/app/services/ocr_workflow.py` | Raw와 Clean을 모두 Job 결과까지 전달 |
| `backend/app/services/admin_ocr.py` | 제목·유형·Raw·Clean·metadata 전달, 해시 계산/중복 정책 호출 |
| `backend/app/repositories/document_repository.py` | 일반/대용량 부모 저장에 신규 컬럼 반영 |
| `backend/app/services/large_document_service.py` | preview/전체 텍스트 의미 구분과 대용량 metadata 결정 |
| `backend/tests/test_ocr_workflow.py` | Raw/Clean 분리와 Job 결과 계약 검증 |
| `backend/tests/test_ocr_vector_save.py` | 일반 저장 신규 컬럼, NULL 호환, hash 정책 검증 |
| `backend/tests/test_large_ocr_vector_save.py` | 대용량 NULL/preview/staged 저장 정책 검증 |

관리자 입력 metadata를 받는 경우 추가 필수 범위다.

| 파일/영역 | 변경 이유 |
|---|---|
| `frontend/src/features/admin/types/ocr.ts` | save request metadata 타입 추가 |
| `frontend/src/features/admin/services/apiAdminAiService.ts` | 확장 save payload 전달 |
| `frontend/src/features/admin/hooks/useOcrTest.ts` | metadata 상태를 저장 요청에 연결 |
| `frontend/src/features/admin/components/ocr/OcrPanel.tsx` 및 하위 입력 컴포넌트 | 관리자 metadata 입력·검증 UI |
| 관련 프론트 테스트 | payload와 입력 검증 회귀 방지 |

신규 metadata를 검색 결과와 Chat 출처에 노출하는 경우 추가 필수 범위다.

| 파일/영역 | 변경 이유 |
|---|---|
| `backend/app/repositories/document_chunk.py` | 부모 출처·metadata를 검색 결과와 함께 조회 |
| `backend/app/services/rag_search_service.py` | `RetrievedChunk`에 source/metadata 매핑 |
| `backend/app/schemas/rag.py` | API 결과 optional source/metadata 추가 |
| `backend/app/api/rag/router.py` | 확장 결과 응답 매핑 |
| `backend/tests/test_rag_search_service.py` 및 RAG API 테스트 | NULL fallback과 source/metadata 검증 |
| 검색 프론트 결과 컴포넌트 | metadata를 실제 표시할 때만 필요 |

### 15.3 직접 수정할 필요가 없는 파일

현재 목표와 위 호환 전략에서는 다음 핵심 영역의 내부 알고리즘 변경이 필요하지 않다.

| 파일/영역 | 수정 불필요 이유 |
|---|---|
| `backend/app/ai/rag/embeddings/remote.py` | 임베딩 공급자 호출 계약 불변 |
| `backend/app/services/embedding_service.py` | 입력 청크와 공급자 처리 불변 |
| `backend/app/ai/rag/hybrid.py` | RRF 결합식 불변 |
| `backend/app/models/generated.py`의 `DocumentChunks`/`ChunkEmbeddings` 컬럼 정의 | 자식 스키마 변경 불필요 |
| 기존 chunk/embedding Migration | 과거 Migration 수정 금지, 새 revision만 추가 |
| `backend/app/services/dashboard_service.py` | 문서 ID count만 사용 |
| `backend/app/repositories/mypage.py` | `uploaded_by` NULL 처리만 사용 |
| `backend/app/services/document_ingestion_service.py` | 현재 호출자가 텍스트를 제공하며 직접 부모 컬럼을 읽지 않음 |
| consultation prompt builder | metadata를 프롬프트 정책에 사용하지 않는 한 불필요 |
| 기존 임베딩 데이터 | 부모 컬럼 추가만으로 재생성할 이유 없음 |

`backend/migrations/env.py`는 코드 수정 대상이 아닐 가능성이 높지만, `target_metadata`가 생성 모델의 Base를 참조하므로 Migration 생성 절차 확인 대상이다.

### 15.4 생성 모델 관리 위험

`backend/scripts/generate_models.py`는 실DB를 반영해 `backend/app/models/generated.py`를 덮어쓴다. 반면 Alembic autogenerate도 이 모델의 Base metadata에 의존한다.

따라서 팀은 아래 순서를 사전에 정해야 한다.

1. 사람이 검토한 수동 Migration을 생성한다.
2. Neon 개발 브랜치/스테이징에 적용한다.
3. 실DB에서 모델을 재생성한다.
4. `metadata` 속성명 충돌과 nullable/type을 검토한다.
5. 애플리케이션 코드를 반영한다.

DB 변경 전에 모델 생성 스크립트를 돌리면 신규 필드가 사라질 수 있고, ORM만 먼저 배포하면 아직 컬럼이 없는 DB를 조회할 때 장애가 날 수 있다. 배포 순서는 nullable 컬럼 Migration 선적용 후 애플리케이션 배포가 안전하다.

---

## 16. Migration 위험 분석

| 위험 | 수준 | 설명 | 완화책 |
|---|---:|---|---|
| 코드 Migration과 실DB 불일치 | 높음 | 초기 Migration이 비어 있어 저장소만으로 전체 기원을 보장하지 못함 | 실스키마와 `alembic_version` 대조 |
| 잘못된 Neon 대상 반영 | 높음 | 프로젝트/브랜치/DB/schema 혼동 가능 | 대상 식별자와 연결 문자열을 사람이 교차 확인 |
| ORM `metadata` 충돌 | 높음 | declarative metadata 속성과 이름 충돌 가능 | DB 컬럼명과 Python 속성명 분리 |
| Raw/Clean 의미 혼재 | 높음 | 기존 행은 Clean, 신규 행은 Raw가 될 수 있음 | legacy 정책·처리 버전·호환 조회 정의 |
| 대용량 preview 오인 | 높음 | 미리보기를 전체 Clean/Raw로 잘못 표기 가능 | NULL 또는 scope metadata 명시 |
| 즉시 unique hash | 중간~높음 | 기존 중복, 의도적 재수집, 동시 저장 충돌 | 초기 비고유 index와 경고 정책 |
| 테이블 lock/DDL 지연 | 낮음~중간 | nullable 컬럼은 비교적 가볍지만 실환경 트래픽 영향 가능 | 스테이징 dry-run, 저트래픽 배포 |
| JSONB 무제한 입력 | 중간 | 키 난립, 크기 증가, 필터 일관성 저하 | Pydantic 구조 검증·통제어 |
| ORM/DB 배포 순서 | 중간 | 모델이 컬럼을 조회하지만 DB에 없으면 실패 | Migration 먼저, 코드 나중 |
| 기존 행 NULL 처리 누락 | 중간 | UI/DTO가 필수 문자열로 가정할 수 있음 | optional 타입과 fallback 테스트 |
| hash 계약 변경 | 중간 | 정제기 변경 때 동일성 기준이 흔들림 | 정제/hash 버전 정책 기록 |

---

## 17. 팀 합의가 필요한 사항

### 17.1 DB/데이터 팀

- 실제 Neon 대상 프로젝트·브랜치·DB·schema
- 현재 `alembic_version`과 신규 `down_revision`
- 모든 신규 컬럼 nullable 여부
- `metadata` DB default를 NULL로 둘지 `{}`로 둘지
- `content_hash` 비고유 index 여부
- 추후 unique 범위: 글로벌, source별, version별 또는 미적용
- 기존 행 backfill 범위와 실행 시점
- 대용량 행 식별 방법

### 17.2 백엔드 팀

- `ocr_extracted_text`의 신규 정확한 의미
- 기존 행은 legacy clean으로 볼지 별도 변환할지
- Raw 텍스트를 Job 메모리/캐시에 추가 보존할지
- clean 정규화 및 SHA-256 입력 계약
- 중복 발견 시 차단, 경고, 기존 문서 반환, 재저장 중 어떤 동작을 할지
- `source_type` 통제값: 초기에는 `file`, `url` 권고
- JSONB 허용 키와 길이·통제어 검증
- generated ORM 갱신 절차

### 17.3 프론트엔드/기획 팀

- metadata를 OCR 실행 전에 받을지, 저장 버튼 시 받을지
- 필수 입력과 자동 추론 항목
- 제목의 기본값과 수정 허용 여부
- 중복 후보 발견 시 사용자 UX
- 검색 결과에 source/title/category/topic을 얼마나 표시할지
- 기존 NULL 문서 표시 문구

### 17.4 RAG/AI 팀

- metadata는 표시만 할지 검색 필터·가중치에 사용할지
- 공식 출처 우선순위가 필요한지
- 필터 적용 시 Jina/BGE 후보 집합에 동일 조건을 적용할지
- 정제기 버전 변경 시 기존 청크·해시·임베딩 재생성 정책
- 대용량 문서 전체 정제 경로의 도입 시점

---

## 18. DB 작업 전 체크리스트

### 18.1 환경과 스키마 — 실DB 확인 필요

- [ ] Neon 프로젝트, 브랜치, database, role, schema가 대상 환경인지 확인
- [ ] 백업 또는 복구 가능한 Neon branch를 준비
- [ ] `alembic_version`의 현재 revision 확인
- [ ] 저장소 기준 head `0dcef89659d1`과의 관계 확인
- [ ] `vector_db.admin_documents`의 실제 컬럼/type/null/default 확인
- [ ] PK, FK, index, cascade 규칙 확인
- [ ] `document_chunks`, `chunk_embeddings`의 실제 구조 확인
- [ ] 운영/개발 환경별 schema drift 확인

### 18.2 기존 데이터 — 실DB 확인 필요

- [ ] 전체 문서 수와 `ocr_status`별 건수 확인
- [ ] `ocr_extracted_text` NULL/빈 문자열/길이 분포 확인
- [ ] 100,000자 미리보기로 추정되는 대용량 행 식별
- [ ] 동일 URL과 동일 본문 후보 확인
- [ ] 기존 metadata를 복원할 출처가 있는지 확인
- [ ] backfill 대상과 제외 대상을 확정

### 18.3 데이터 계약

- [ ] `ocr_extracted_text = Raw`, `cleaned_text = Clean` 합의
- [ ] 기존 행의 legacy 의미와 fallback 합의
- [ ] 대용량 문서의 NULL/preview 처리 합의
- [ ] `source_type` 통제값 합의
- [ ] metadata 최소 키와 검증 규칙 합의
- [ ] hash 입력 정규화, 알고리즘, case, 버전 합의
- [ ] 중복 탐지 후 서비스 동작 합의

### 18.4 Migration/배포

- [ ] 신규 revision의 `down_revision` 확인
- [ ] 신규 컬럼을 nullable로 생성
- [ ] PostgreSQL JSONB 타입과 ORM 별칭 확인
- [ ] `content_hash` 비고유 index 이름 확인
- [ ] Migration downgrade 범위와 데이터 손실 경고 검토
- [ ] Neon 개발 브랜치/스테이징에서 upgrade dry-run
- [ ] DDL 수행 시간과 lock 확인
- [ ] Migration 선적용 → ORM/애플리케이션 배포 순서 확정
- [ ] DB 적용 후 모델 재생성 및 diff 검토

### 18.5 회귀 검증

- [ ] 기존 NULL 문서 검색 성공
- [ ] 일반 파일 저장 시 Raw/Clean/제목/유형/metadata/hash 검증
- [ ] URL 저장 검증
- [ ] 대용량 staged 저장과 실패 보상 삭제 검증
- [ ] Jina 검색 결과 비교
- [ ] BGE 검색 결과 비교
- [ ] RRF 결과와 순위 회귀 확인
- [ ] 검색 API의 source/metadata optional 처리 확인
- [ ] 상담 Chat 컨텍스트 source 처리 확인
- [ ] 대시보드 count와 사용자 삭제 흐름 확인
- [ ] 외부 임베딩 호출이 중복 저장 정책과 일치하는지 확인

---

## 19. 단계별 권장 실행 순서

이번 보고서는 실행하지 않았으며, 실제 승인 후 권장 순서는 다음과 같다.

### 1단계: 계약 확정

- B안 채택
- nullable 정책 확정
- Raw/Clean 의미 확정
- metadata 키와 `source_type` 통제값 확정
- hash와 중복 처리 정책 확정
- 대용량 예외 확정

### 2단계: 실DB 점검

- Neon 브랜치와 schema 확인
- Alembic revision 확인
- 데이터 분포와 중복 조사
- 스테이징 branch 준비

### 3단계: 호환 Migration

- 부모 테이블에 nullable 5개 컬럼 추가
- `content_hash` 비고유 index 추가
- 자식 테이블은 변경하지 않음
- 즉시 backfill/NOT NULL/unique는 하지 않음

### 4단계: 저장 경로 반영

- 일반 OCR에서 Raw/Clean 분리
- 제목·유형·metadata·hash 저장
- 대용량은 전체 Clean/hash 준비 전 NULL 정책 적용
- fake repository와 회귀 테스트 갱신

### 5단계: 조회 활용

- 검색 결과에 source/metadata를 optional로 제공
- 기존 NULL fallback 적용
- 필요 시에만 metadata 필터 도입

### 6단계: 데이터 정비

- 기존 행을 유형별로 선별 backfill
- 중복 후보 검토
- 운영 결과 후 NOT NULL 또는 부분 unique 여부 재평가

---

## 20. 지시문 핵심 질문에 대한 최종 답변

### 1) `admin_documents`만 확장하면 충분한가?

**현재 30건 내외의 RAG 문서 정제·출처·분류·중복 탐지 목적에는 충분하다.** 별도 문서 마스터 테이블은 버전 관리, 다중 원본, 승인 워크플로, 다국어 판본 같은 요구가 확정될 때 검토한다.

### 2) `document_chunks`와 `chunk_embeddings`는 정말 변경하지 않아도 되는가?

**그렇다.** 이번 신규 정보는 문서 단위 속성이고, 두 자식 테이블은 이미 청크 본문과 공급자별 벡터를 저장한다. 부모 FK/PK와 청크 의미가 유지되므로 스키마 변경이 필요 없다.

### 3) 컬럼 추가가 Jina/BGE/RRF를 깨뜨리는가?

**깨뜨리지 않는다.** 신규 컬럼을 nullable로 추가하고 기존 검색 쿼리를 유지하면 임베딩 모델, 벡터 차원, 후보 조회, RRF 식은 모두 불변이다. metadata 필터를 새로 넣을 때만 검색 쿼리와 테스트가 추가된다.

### 4) 기존 행의 신규 컬럼이 NULL이면 문제가 되는가?

**현재 검색에는 문제가 없다.** API/화면에서 optional과 fallback을 지키면 된다. 문제는 NOT NULL, 전면 필터, unique, 완전한 중복 탐지를 요구할 때 발생하며 그 전에는 backfill이 선택 사항이다.

### 5) `ocr_extracted_text` 의미를 Raw로 바꾸면 어디가 영향을 받는가?

OCR Job 결과, `ocr_workflow`, 저장 서비스, repository 시그니처, 문서 미리보기/내보내기/재처리, 대용량 preview 정의, 테스트와 데이터 사전이 영향을 받는다. 현재 온라인 RAG 검색은 `chunk_text`를 사용하므로 직접 영향은 없다. 기존 행은 Clean이 들어 있어 신규 Raw 행과 의미가 혼재한다는 점이 가장 큰 위험이다.

### 6) `cleaned_text`는 어디에서 우선 사용해야 하는가?

청킹, 임베딩 원천, content hash, 문서 미리보기·내보내기, 재청킹·재임베딩에서 우선 사용한다. 기존 행 문서 조회는 `COALESCE(cleaned_text, ocr_extracted_text)`를 사용한다. 청크 검색 본문은 계속 `document_chunks.chunk_text`를 사용한다.

### 7) `metadata JSONB`의 ORM 이름 충돌은 어떻게 처리하는가?

DB 컬럼은 `metadata`로 만들고 Python ORM 속성은 `document_metadata`처럼 별칭 매핑한다. generated model 재생성 결과가 이 충돌을 올바르게 처리하는지 반드시 검토한다.

### 8) `content_hash`는 지금 넣을 것인가, 나중에 넣을 것인가?

**지금 넣는 B안을 권고한다.** 단, nullable + 비고유 index로 시작한다. 최종 전체 Clean 텍스트의 SHA-256 계약을 확정하고 서비스 레벨에서 중복 후보를 알린다. unique는 실데이터와 운영 정책 확인 후 판단한다.

### 9) Migration 전에 사람이 반드시 확인할 것은 무엇인가?

Neon 대상 환경, 실스키마, `alembic_version`, 코드 head와의 관계, 기존 데이터/대용량/중복 분포, Raw/Clean 계약, metadata 통제어, hash 정규화, unique 여부, 배포 순서, 생성 모델 갱신 절차다. 이 항목들은 **실DB 확인 필요**를 포함한다.

### 10) 팀이 최종 합의해야 할 정확한 DB 변경은 무엇인가?

다음 변경을 권고 합의안으로 제시한다.

```text
대상: vector_db.admin_documents

추가:
- document_title VARCHAR(255) NULL
- source_type VARCHAR(30) NULL
- cleaned_text TEXT NULL
- metadata JSONB NULL
- content_hash VARCHAR(64) NULL

인덱스:
- content_hash 비고유 B-tree index

유지:
- 기존 PK/FK/cascade
- document_chunks 스키마
- chunk_embeddings 스키마와 벡터 차원

초기 미적용:
- 신규 컬럼 NOT NULL
- metadata 강제 DB default
- content_hash unique
- 일괄 backfill
- 재청킹/재임베딩
```

이 안은 코드 기준 권고안이며, 실제 확정 전 실DB 점검과 담당 팀 승인이 필요하다.

---

## 21. 최종 권고

**B안으로 `admin_documents`만 호환 확장하고, 자식 청크/임베딩 테이블은 유지한다.** 첫 단계에서는 nullable 5개 컬럼과 `content_hash` 비고유 index만 추가하는 것이 가장 안전하다.

구현의 핵심은 컬럼 추가 자체보다 데이터 의미를 고정하는 것이다. 일반 문서는 Raw와 Clean을 분리하고, `cleaned_text`를 청킹·해시의 기준으로 삼아야 한다. 대용량 문서는 현재 전체 정제 텍스트가 없으므로 NULL/preview 예외를 명시해야 한다. JSONB는 제한된 스키마로 검증하고 ORM에서는 `document_metadata` 별칭을 사용한다.

실제 DB 작업은 Neon 실스키마와 Alembic 상태를 확인한 뒤에만 진행해야 한다. 이 보고서 작성 과정에서는 코드, DB, Migration, ORM, Neon 데이터, 임베딩을 변경하지 않았다.
