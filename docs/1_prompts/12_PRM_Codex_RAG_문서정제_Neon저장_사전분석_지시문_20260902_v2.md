# Codex 지시문 — MediSense RAG 문서 정제·Neon 저장 구조 사전분석

## 0. 이번 작업의 목표

이번 작업은 **구현이 아니라 사전 분석**이다.

최종적으로 만들고 싶은 기능은 다음과 같다.

```text
Admin RAG 탭(구 OCR 탭)
→ 파일 또는 웹 URL 입력
→ 텍스트 추출
   - 문서 본문 텍스트
   - 웹페이지 본문 텍스트
   - 필요한 경우 이미지 OCR 텍스트
→ RAG용 텍스트 정제
→ 필요한 Metadata 부여
→ Chunk 분할
→ Embedding
   - jina-v4
   - medical-bgem3
→ Neon PostgreSQL + pgvector 저장
```

현재 프로젝트에 이미 구현된 기능을 최대한 재사용하고,
**정제된 RAG 문서를 Neon에 안정적으로 저장하기 위해 무엇을 알아야 하는지, 현재 DB 구조가 적합한지, 어떤 변경이 필요한지, 실제 구현이 가능한지**를 먼저 파악한다.

이번 단계에서는 코드를 수정하지 않는다.

---

# 1. 반드시 참고할 문서

프로젝트에 아래 문서가 존재하면 우선 읽고 현재 코드와 비교한다.

## 1.1 RAG 파이프라인 설계 문서

참고 개념:

```text
의료 자료 수집
→ 텍스트 추출
→ 정제
→ Chunking
→ Metadata 생성
→ Jina + BGE-M3 Embedding
→ Neon pgvector 저장
```

의료 Metadata 예시:

```json
{
  "category": "red_flag",
  "symptoms": ["두통"],
  "department": ["신경과"],
  "source": "공식 의료기관",
  "document_title": "두통 관련 건강정보",
  "source_url": "...",
  "license": "확인 필요"
}
```

단, 위 Metadata 전체를 이번 구현에서 반드시 사용한다고 가정하지 않는다.

이번 분석의 핵심은 **현재 프로젝트에 필요한 최소 Metadata가 무엇인지 판단하는 것**이다.

---

## 1.2 현재 Neon 저장 구조 문서

현재 문서 기준 저장 구조:

```text
vector_db.admin_documents 1행
└─ vector_db.document_chunks N행
   └─ vector_db.chunk_embeddings N × 2행
      ├─ jina-v4
      └─ medical-bgem3
```

현재 문서 기준 저장 흐름:

```text
Admin RAG 탭
→ 파일 또는 웹 URL 분석 Job 완료
→ 추출 텍스트 Chunk 분할
→ POST /api/admin/ocr/vector-save
→ Jina passage Embedding 생성
→ Medical BGE-M3 passage Embedding 생성
→ admin_documents INSERT
→ document_chunks INSERT
→ chunk_embeddings INSERT
→ 하나의 Transaction으로 COMMIT
```

현재 관련 코드로 기록된 경로:

```text
frontend/src/features/admin/components/ocr/OcrPanel.tsx

backend/app/api/admin/router.py
backend/app/services/admin_ocr.py
backend/app/services/embedding_service.py
backend/app/repositories/document_repository.py
backend/app/repositories/document_chunk.py
backend/app/services/rag_search_service.py
backend/app/models/generated.py
```

이 경로는 문서 기록일 뿐이므로 실제 프로젝트에서 존재 여부와 현재 구현을 직접 확인한다.

---

# 2. 이번 분석 범위

이번 분석은 **RAG 데이터 적재 파이프라인**에 집중한다.

핵심 범위:

```text
입력
→ 텍스트 추출
→ 이미지 OCR
→ 정제
→ Metadata
→ Chunk
→ Embedding
→ Neon 저장
```

다음은 이번 분석의 중심 범위가 아니다.

```text
사용자 Chat UI 전체 구조
LLM Fine-tuning
최종 상담 Prompt 전체 재설계
진료과 분류 전체 구현
RRF 알고리즘 재설계
```

다만 기존 RRF/검색 기능이 저장 Schema와 직접 연결되어 있다면,
**DB 변경 시 기존 검색이 깨지는지 확인하기 위한 수준에서만 분석**한다.

---

# 3. 절대 원칙

## 3.1 문서 내용만 믿지 말 것

반드시 실제 코드와 ORM/DB 정의를 직접 확인한다.

다음 세 상태를 구분한다.

```text
1. 문서와 실제 코드가 일치
2. 문서에는 있으나 실제 코드는 다름
3. 문서에는 없지만 실제 코드에는 구현됨
```

---

## 3.2 기존 구조를 최대한 유지할 것

이번 분석의 목표는 새로운 RAG 프레임워크를 도입하는 것이 아니다.

우선순위:

```text
현재 RAG 탭 재사용
현재 OCR/HTML 추출 기능 재사용
현재 Chunk 기능 재사용
현재 Jina/BGE Embedding 재사용
현재 Neon 저장 구조 재사용
```

그 위에 **정제 + Metadata 저장**을 최소 변경으로 추가할 수 있는지 검토한다.

---


# 3.3 프로젝트 전체의 다른 팀원 RAG 관련 구현 탐색

현재 분석 대상 파일만 보지 말고, **프로젝트 전체에서 다른 팀원이 이미 구현한 RAG 관련 기능이 있는지 반드시 조사한다.**

목적은 새 기능을 중복 구현하지 않고, 기존 구현을 재사용하거나 연결할 수 있는지 판단하는 것이다.

## 조사 범위

프로젝트 전체에서 다음 키워드와 개념을 기준으로 파일/코드/문서를 검색한다.

```text
rag
retrieval
vector
embedding
pgvector
jina
bge
rrf
chunk
chunking
metadata
clean
cleaning
preprocess
normalize
document
knowledge
dataset
huggingface
department
red_flag
symptom
classification
search
similarity
top_k
```

단순 파일명 검색만 하지 말고 다음까지 확인한다.

```text
Backend Router
Service
Repository
Schema / Model
Utility
Frontend Admin 기능
실제 Chat 기능
Test
Script
docs / reports
migration
config
```

## Git 이력도 비파괴적으로 확인

가능하면 현재 저장소의 Git 이력을 이용해
다른 팀원이 구현한 RAG 관련 기능의 존재 여부를 확인한다.

허용 예:

```text
git log
git log --all
git branch -a
git show <commit>
git diff <commit>..<commit> -- <path>
git blame
```

다음은 하지 않는다.

```text
checkout
switch
reset
rebase
merge
cherry-pick
commit
push
```

Git 작성자/커밋 메시지를 통해 구현 주체를 확인할 수 있으면 기록하되,
확실하지 않으면 특정 팀원의 작업이라고 단정하지 않는다.

## 특히 확인할 기능

다음 기능이 현재 분석 대상 코드 외 다른 위치에 이미 존재하는지 확인한다.

```text
RAG 문서 전처리
텍스트 정제
Metadata 생성
Metadata 저장
의료 증상/질환 분류
진료과 분류
Red Flag 판별
의미 단위 Chunking
Token 기반 Chunking
Embedding 생성
Jina/BGE 이외 Embedding
Vector Search
Hybrid Search
RRF
Top-K 후처리
인접 Chunk 확장
중복 문서 방지
재임베딩 / Backfill
Hugging Face Dataset 처리
CSV / JSON / JSONL RAG 데이터 적재
실제 사용자 Chat과 RAG 연결
RAG 평가 스크립트
```

## 중복 및 재사용 가능성 분석

발견한 기능마다 다음을 구분한다.

| 기능 | 위치 | 현재 사용 여부 | 현재 RAG 탭과 중복 여부 | 재사용 가능성 | 연결 시 주의점 |
|---|---|---|---|---|---|

특히 다음 세 경우를 명확히 구분한다.

```text
1. 이미 사용 중인 공통 기능
2. 구현되어 있으나 현재 RAG 탭에서 사용하지 않는 기능
3. 과거/실험용/레거시 구현
```

코드가 존재한다는 이유만으로 바로 재사용 가능하다고 판단하지 말고,
현재 호출 관계와 의존성을 확인한다.

## 문서와 실제 구현 비교

프로젝트 내 다른 팀원이 작성한 RAG 관련 보고서/설계 문서가 있으면 함께 찾아본다.

각 문서에 대해:

```text
문서에서 주장하는 기능
→ 실제 코드 존재 여부
→ 현재 실행 경로에 연결되어 있는지
```

를 비교한다.

문서만 존재하고 코드가 없으면 `문서상 설계만 존재`,
코드는 있으나 호출되지 않으면 `미연결 구현`,
실제 Call Flow에 포함되면 `현재 사용 중`으로 분류한다.

## 최종 목적

이 조사를 통해 후속 구현 전에 반드시 다음을 판단한다.

```text
- 다른 팀원이 이미 만든 정제 기능이 있는가?
- Metadata 관련 코드가 이미 있는가?
- 별도 RAG 적재 파이프라인이 중복으로 존재하는가?
- 현재 Admin RAG 탭과 통합 가능한 코드가 있는가?
- 새로 만들 필요 없이 재사용 가능한 기능은 무엇인가?
- 서로 다른 구현이 충돌할 가능성이 있는가?
```


# 4. 현재 RAG 탭 입력 흐름 분석

실제 코드에서 다음 입력들이 어떻게 처리되는지 추적한다.

```text
파일 업로드
웹 URL
PDF
PNG/JPG
DOCX
PPTX
HTML
```

각 입력에 대해 Call Flow를 작성한다.

예:

```text
Frontend
→ API
→ Service
→ Parser/OCR
→ 분석 Job
→ Text
→ Chunk
→ Embedding
→ Repository
→ Neon
```

반드시 확인:

- RAG 탭의 실제 Frontend Component
- 구 OCR 이름이 내부 코드에 얼마나 남아 있는지
- 파일 업로드 API
- URL 분석 API
- HTML 본문 추출 코드
- HTML 내부 이미지 수집 코드
- 이미지 OCR 코드
- OCR 텍스트와 HTML 본문 텍스트를 합치는 위치
- 추출 결과 Preview
- Chunk Preview
- VectorDB 저장 버튼
- 저장 요청에 실제로 전달되는 데이터

---

# 5. 현재 추출 텍스트의 형태 확인

RAG 탭에서 최종적으로 Chunking에 전달되는 문자열이 정확히 무엇인지 확인한다.

예:

```text
HTML 본문
+
이미지 OCR 텍스트
```

인지,

```text
HTML 전체 get_text()
+
이미지 OCR
```

인지,

또는 별도 구조체를 사용하고 있는지 확인한다.

특히 다음을 조사한다.

- 제목이 포함되는가
- 소제목/heading이 보존되는가
- 표가 어떤 형태로 변환되는가
- 이미지 OCR 결과가 본문의 어느 위치에 삽입되는가
- 이미지 OCR 결과에 출처 또는 구분자가 붙는가
- 메뉴/푸터/버튼/네비게이션이 섞이는가
- 중복 문장이 생기는가
- OCR 오류가 포함되는가

가능하면 실제 저장 전 데이터 구조를 예시로 보여준다.

---

# 6. 텍스트 정제 현황 분석

팀 설계의 핵심 추가 요구사항은 다음이다.

```text
추출 Text
→ 정제된 RAG Text
```

현재 코드에 실제 정제 로직이 어느 정도 존재하는지 확인한다.

## 6.1 자동으로 확인할 정제 항목

```text
HTML nav 제거
header 제거
footer 제거
script/style 제거
메뉴/버튼 텍스트 제거
공백 정규화
빈 줄 정리
중복 라인 제거
중복 문단 제거
깨진 문자 정리
OCR 특수문자 노이즈 정리
불필요한 URL 텍스트 제거
본문과 이미지 OCR 중복 제거
```

각 항목을 다음 표로 정리한다.

| 정제 항목 | 현재 구현 | 구현 위치 | 문제점 | 추가 필요 여부 |
|---|---|---|---|---|

---

# 7. 정제 단계의 적절한 위치 판단

현재 파이프라인에서 정제를 어디에 넣는 것이 가장 적절한지 분석한다.

후보:

### A.

```text
HTML/OCR 추출 중 정제
→ Text
→ Chunk
```

### B.

```text
HTML/OCR 추출
→ Raw Text 저장
→ Cleaning Service
→ Clean Text
→ Chunk
```

### C.

```text
HTML/OCR 추출
→ Chunk
→ Chunk별 정제
```

각 방식의 장단점을 현재 코드 기준으로 평가한다.

최종적으로 **기존 구조를 가장 적게 변경하면서 재사용 가능한 위치**를 추천한다.

---

# 8. 원본과 정제본을 모두 저장해야 하는지 분석

현재 `admin_documents.ocr_extracted_text`에는 전체 추출 텍스트가 저장되는 것으로 문서에 기록되어 있다.

정제 기능 추가 시 다음 선택지를 비교한다.

## 선택 1

```text
ocr_extracted_text
= 정제 전 원본 Text
```

추가:

```text
cleaned_text
```

## 선택 2

```text
ocr_extracted_text
= 정제된 Text로 교체
```

## 선택 3

별도 Document Revision/Processing 테이블

이번 프로젝트 규모에서는 과도한 구조를 피한다.

다음 기준으로 판단한다.

- 원본 추적 가능성
- 정제 실패 시 복구
- DB 중복 저장량
- 기존 코드 호환성
- 마감 일정
- 검색/재임베딩 편의성

---

# 9. RAG Metadata 최소 요구사항 분석

팀 문서에는 많은 의료 Metadata가 제안되어 있지만,
이번 단계에서는 **Neon 저장을 위해 실제로 필요한 최소 Metadata부터 정의**한다.

우선 후보:

```text
document_id
title
source_url
source_type
source_name
category
topic
language
license
created_at / collected_at
```

의료 Metadata 후보:

```text
symptoms
disease
department
red_flag
```

각 Metadata를 다음 세 그룹으로 분류한다.

### 필수

없으면 문서 관리나 검색 추적이 어려움.

### 권장

RAG 품질 향상에 유용하지만 없어도 저장은 가능.

### 후순위

현재 30개 내외 문서 규모에서는 나중에 추가 가능.

표:

| Metadata | 우선도 | 생성 방식 | 저장 위치 제안 | 이유 |
|---|---|---|---|---|

---

# 10. Metadata 생성 방식 분석

Metadata를 어떻게 생성할 수 있는지 현실적으로 분석한다.

다음 방식을 비교한다.

## 10.1 입력 시 사용자 직접 입력

예:

```text
문서명
출처기관
대분류
주제
URL
```

## 10.2 URL/HTML에서 자동 추출

예:

```text
title
source_url
domain
language
```

## 10.3 규칙 기반 자동 분류

예:

```text
특정 keyword → category/topic 후보
```

## 10.4 LLM을 이용한 구조화

예:

```text
정제된 문서
→ 증상/진료과/Red Flag 후보 추출
→ JSON
```

## 10.5 외부 관리 파일 사용

예:

```text
Excel / CSV / JSON
→ 문서 ID 기준 Metadata 연결
```

현재 프로젝트의 약 30개 내외 자료 규모를 고려하여,
**가장 구현 부담이 적고 재현 가능한 방식**을 추천한다.

Hugging Face Dataset 사용 여부도 여기에서 평가한다.

Hugging Face를 반드시 도입해야 한다고 가정하지 않는다.

---

# 11. 현재 Neon DB Schema 전체 분석

실제 ORM / Migration / Repository를 확인하여 아래 세 테이블의 현재 정의를 정리한다.

```text
vector_db.admin_documents
vector_db.document_chunks
vector_db.chunk_embeddings
```

각 테이블에 대해:

- Column
- Type
- Nullable
- PK
- FK
- Unique
- Index
- Default
- 실제 사용 여부

를 표로 작성한다.

---

# 12. `admin_documents` 변경 필요성 분석

현재 문서상 컬럼:

```text
id
original_file_url
ocr_extracted_text
ocr_status
uploaded_by
created_at
```

정제/Metadata 저장을 위해 추가가 필요한지 검토한다.

후보:

```text
document_title
source_name
source_type
category
topic
cleaned_text
metadata JSONB
updated_at
content_hash
```

무조건 전부 추가하지 않는다.

각 후보마다:

```text
필요
권장
불필요
```

로 평가한다.

---

# 13. `document_chunks` 변경 필요성 분석

현재 문서상 컬럼:

```text
id
document_id
chunk_index
chunk_text
embedding (legacy Gemini)
created_at
```

다음이 필요한지 확인한다.

```text
chunk_metadata JSONB
section_title
token_count
char_count
cleaning_version
```

특히 **문서 Metadata를 Chunk마다 복제할 필요가 있는지**,
아니면 `document_id` Join으로 충분한지 평가한다.

불필요한 데이터 중복을 피한다.

---

# 14. `chunk_embeddings` 변경 필요성 분석

현재 구조:

```text
id
chunk_id
provider_name
dimension
embedding
created_at
```

현재 Jina/BGE 이중 임베딩 구조가 정제된 텍스트에도 그대로 사용 가능한지 확인한다.

확인:

- 정제 전 Text가 아니라 정제 후 Chunk를 Embedding하도록 변경 가능한지
- 현재 Repository 재사용 가능 여부
- 기존 검색/RRF와 호환되는지
- Schema 변경이 실제로 필요한지

가능하면 이 테이블은 변경하지 않는 방향을 우선 검토한다.

---

# 15. 기존 Gemini 레거시 컬럼 분석

현재:

```text
document_chunks.embedding
```

은 기존 Gemini용 레거시 컬럼이고,
Jina/BGE 신규 흐름에서는 NULL이라고 문서에 기록되어 있다.

실제 코드에서도 동일한지 확인한다.

이번 정제 기능 구현과 관계없이:

```text
유지
삭제 후보
완전 미사용
```

중 어디에 해당하는지 분석만 한다.

이번 단계에서는 삭제하지 않는다.

---

# 16. Raw → Clean → Chunk 데이터 흐름 설계 가능성

현재 코드에 아래 형태를 최소 변경으로 적용 가능한지 판단한다.

```text
[Source]

File / URL
   ↓

[Extraction]

HTML Text
Document Text
Image OCR Text
   ↓

[Raw Document]

raw_text
   ↓

[Cleaning]

clean_text
   ↓

[RAG Document]

title
source
category
topic
metadata
clean_text
   ↓

[Chunking]

Chunk 0
Chunk 1
Chunk 2
...
   ↓

[Embedding]

Jina
BGE
   ↓

[Neon]

admin_documents
document_chunks
chunk_embeddings
```

이 구조가 현재 코드에 얼마나 자연스럽게 들어가는지 평가한다.

---

# 17. Cleaning Service 구현 가능 여부

실제 코드 구조를 확인하여 다음과 같은 독립 Service 추가가 가능한지 검토한다.

예:

```text
rag_document_cleaner.py
document_cleaning_service.py
rag_preprocess_service.py
```

예상 책임:

```text
clean(raw_text, source_type, metadata)
→ cleaned_text
```

가능하면 OCR/HTML Parser 내부에 정제 규칙을 분산시키기보다,
**공통 정제 레이어를 둘 수 있는지**를 우선 검토한다.

하지만 기존 구조상 별도 Service가 오히려 과도하다면 그 이유를 명시한다.

---

# 18. 이미지 OCR 텍스트 처리 방식 분석

이번 목표에 반드시 포함되는 부분이다.

웹/문서 내 이미지 OCR 결과가 현재:

```text
본문 뒤에 단순 append
```

인지,

```text
원래 이미지 위치에 삽입
```

인지,

```text
별도 field
```

인지 확인한다.

정제 시 이미지 OCR 텍스트를 어떻게 처리하는 것이 좋은지 분석한다.

예:

```text
[본문]
...

[이미지 OCR]
...
```

또는

```text
section_title
image_alt
ocr_text
```

등.

다음 문제도 확인한다.

- 동일 내용이 HTML alt와 OCR 양쪽에 중복
- 이미지 메뉴/배너 OCR
- 작은 아이콘 OCR
- OCR 오인식
- 의료 도표에서 의미 없는 단어만 추출되는 문제

이번 단계에서는 Vision LLM 도입을 기본안으로 잡지 않는다.

---

# 19. Chunking과 정제 순서 확인

반드시 다음 순서를 기준으로 검토한다.

```text
Text 추출
→ 정제
→ Chunk
→ Embedding
```

현재 코드가:

```text
Text 추출
→ Chunk
→ 정제 없음
```

이라면 변경 포인트를 분석한다.

또한 팀 문서의 권장값:

```text
500~800 tokens
Overlap 100 tokens
```

과 현재 Admin의 실제 Chunk 방식이:

```text
글자 수
Token 수
문장 단위
문단 단위
```

중 무엇인지 확인한다.

이번 분석에서는 Chunk 전략 자체를 전면 재설계하지 않는다.

정제된 Text가 현재 Chunker에 정상적으로 전달될 수 있는지만 우선 평가한다.

---

# 20. 저장 API 변경 필요성 분석

현재 문서 기준 저장 Endpoint:

```text
POST /api/admin/ocr/vector-save
```

현재 요청 Payload와 Backend 흐름을 확인한다.

정제 기능 추가 시:

```text
raw_text
cleaned_text
metadata
chunk_config
```

중 어떤 데이터를 Frontend에서 보내야 하고,
어떤 데이터는 Backend가 보유하고 있어야 하는지 분석한다.

가능하면 Frontend가 거대한 전체 Text/Vector를 다시 보내는 구조는 피한다.

Job 또는 Backend 상태를 재사용할 수 있는지 확인한다.

---

# 21. Transaction 구조 유지 가능 여부

현재 문서에 따르면:

```text
admin_documents
document_chunks
chunk_embeddings
```

저장이 하나의 Transaction으로 처리된다.

정제/Metadata 추가 후에도 다음 원칙을 유지할 수 있는지 확인한다.

```text
문서 저장 성공
+
Chunk 저장 성공
+
Jina/BGE Embedding 저장 성공
=
COMMIT

하나라도 실패
=
ROLLBACK
```

정제 자체는 DB Transaction 전에 끝내는 것이 적절한지 평가한다.

---

# 22. 중복 문서 처리

현재 동일 URL을 다시 저장하면 중복 데이터가 생성되는 것으로 문서에 기록되어 있다.

정제 기능을 넣기 전에 다음을 분석한다.

```text
URL 기준 중복
파일 Hash 기준 중복
정제 Text Hash 기준 중복
사용자가 의도적으로 재등록한 새 버전
```

이번 프로젝트 범위에서 가장 간단한 정책을 제안한다.

단, 이번 단계에서는 구현하지 않는다.

---

# 23. 기존 데이터 호환성

현재 Neon에는:

```text
기존 Gemini Chunk
기존 Text-only Chunk
새 Jina/BGE Chunk
```

등이 섞여 있을 가능성이 있다.

DB 변경을 제안할 경우 반드시 분석한다.

- 기존 데이터가 깨지는가
- NULL 허용으로 호환 가능한가
- Migration만 하면 되는가
- 재임베딩이 필요한가
- 기존 자료를 버려도 되는 개발 데이터인지

---

# 24. Hugging Face Dataset 필요성 분석

팀 논의에서 Hugging Face Dataset을 데이터 정제 중간 단계로 사용하는 의견이 있었다.

현재 목표:

```text
RAG 탭
→ 추출 Text
→ 정제
→ Neon 저장
```

에 Hugging Face가 반드시 필요한지 평가한다.

다음 기준으로 판단한다.

- 현재 의료자료 약 30개
- Admin에서 수동 등록
- 재현 가능한 정제 필요
- 향후 대량 Dataset 확장 가능성
- 코드 복잡도
- 일정

결론은 다음 중 하나로 내려야 한다.

```text
현재 필요
현재는 불필요
선택 기능으로 적합
향후 대량 처리 시 도입 권장
```

---

# 25. 구현 가능 여부 판단

최종적으로 현재 프로젝트에서 다음 기능 구현이 가능한지 판단한다.

```text
RAG 탭에서 추출된 Text
+
이미지 OCR Text
↓
자동 기본 정제
↓
Metadata 연결
↓
정제 결과 Preview
↓
기존 Chunker
↓
기존 Jina/BGE Embedding
↓
기존 Neon 저장
```

판정:

```text
현재 구조에서 쉽게 가능
일부 구조 변경 후 가능
DB Migration 필요
대규모 재설계 필요
```

중 하나로 선택한다.

---

# 26. Gap Analysis

반드시 다음 표를 작성한다.

| 영역 | 목표 | 현재 구현 | 상태 | 필요한 작업 | DB 변경 |
|---|---|---|---|---|---|
| 파일 Text 추출 | 지원 | ? | ? | ? | ? |
| HTML Text 추출 | 지원 | ? | ? | ? | ? |
| 이미지 OCR | 지원 | ? | ? | ? | ? |
| Raw Text 보관 | 필요 여부 판단 | ? | ? | ? | ? |
| Text 정제 | 필요 | ? | ? | ? | ? |
| Metadata | 최소 구성 필요 | ? | ? | ? | ? |
| Chunk | 기존 재사용 목표 | ? | ? | ? | ? |
| Jina Embedding | 기존 재사용 | ? | ? | ? | ? |
| BGE Embedding | 기존 재사용 | ? | ? | ? | ? |
| Neon 저장 | 기존 재사용 | ? | ? | ? | ? |
| 중복 방지 | 정책 필요 | ? | ? | ? | ? |

상태는 다음으로 통일한다.

```text
완료
부분 구현
미구현
확인 필요
```

---

# 27. DB 변경안은 최소안과 확장안으로 분리

DB 변경이 필요하다고 판단하면 하나의 거대한 Schema를 제안하지 않는다.

반드시 두 가지로 나눈다.

## 최소 변경안

프로젝트 완료를 위해 필요한 최소 변경.

예:

```text
admin_documents에
- title
- source_type
- metadata JSONB
- cleaned_text
추가 여부 검토
```

## 확장안

향후 품질 개선/대량 데이터 처리를 고려한 구조.

두 안의 장단점과 작업량을 비교한다.

---

# 28. 예상 수정 파일 목록

실제 코드를 확인한 뒤,
구현 시 수정이 예상되는 파일만 나열한다.

예:

```text
Frontend
- RAG Panel
- API client / types

Backend
- Router
- Admin RAG/OCR Service
- Text Cleaning Service
- Schema
- Repository

DB
- ORM Model
- Migration
```

각 파일마다:

```text
왜 수정하는가
어떤 책임이 추가되는가
```

를 한 줄로 설명한다.

---

# 29. 구현 순서 제안

분석 결과를 바탕으로 실제 후속 구현을 작은 단위로 나눈다.

예시:

```text
1. 현재 Raw Text 흐름 확정
2. Cleaning 규칙 정의
3. Cleaning Service 구현
4. 정제 결과 Preview 연결
5. Metadata 최소 Schema 확정
6. DB Migration
7. Document 저장 로직 연결
8. 기존 Chunk/Embedding 재사용
9. Neon 적재 검증
10. 기존 RRF 검색 회귀 테스트
```

실제 코드를 보고 필요한 순서로 수정한다.

---

# 30. 작업량/위험도 평가

후속 작업마다 다음을 평가한다.

```text
작업량: 소 / 중 / 대
위험도: 낮음 / 보통 / 높음
```

특히 다음 위험을 별도 기록한다.

- DB Migration
- 기존 데이터 호환
- 기존 RRF 검색 영향
- HTML 사이트별 정제 편차
- OCR 중복
- Metadata 자동 생성 정확도
- 동일 문서 중복 저장

---

# 31. 이번 단계에서 하지 말 것

이번 작업에서는 다음을 절대 수행하지 않는다.

```text
코드 수정
DB ALTER
Migration 생성/실행
Neon 데이터 변경
재임베딩
외부 Embedding API 호출
패키지 설치
.env 수정
API Key 변경
Git commit
Git push
Branch merge
```

허용:

```text
코드 읽기
파일 검색
ORM 확인
Migration 파일 확인
Git status/log 확인
비파괴적 DB Schema 코드 확인
문서 읽기
```

실제 Neon에 접속해야만 확인 가능한 사항은
접속/수정하지 말고 **"실DB 확인 필요"**로 표시한다.

---

# 32. 최종 분석 보고서

Markdown 보고서를 생성한다.

권장 파일명:

```text
docs/2_reports/17_RPT_RAG_문서정제_Neon저장_사전분석_20260902.md
```

기존 번호와 충돌하면 프로젝트 문서 규칙에 맞춰 번호를 조정한다.

보고서 구성:

```text
1. 분석 목적
2. 목표 파이프라인
3. 현재 실제 파이프라인
4. 파일/URL/Text/OCR 처리 현황
5. 현재 Raw Text 구조
6. Text 정제 현황
7. 정제 기능 추가 위치 분석
8. 이미지 OCR Text 처리 현황
9. Metadata 현황 및 최소 요구사항
10. Chunking 현황
11. Jina/BGE Embedding 현황
12. Neon DB 현재 구조
13. DB 변경 필요성
14. 최소 DB 변경안
15. 확장 DB 변경안
16. 기존 데이터 호환성
17. 중복 등록 문제
18. Hugging Face Dataset 필요성
19. 구현 가능 여부
20. Gap Analysis
21. 예상 수정 파일
22. 권장 구현 순서
23. 작업량 및 위험 요소
24. 다른 팀원 RAG 관련 구현 및 재사용 가능성
25. 최종 결론
```

---

# 33. 보고서 마지막에 반드시 답할 질문

## Q1.

현재 RAG 탭에서 최종적으로 Chunk에 전달되는 Text는 정확히 어떤 형태인가?

## Q2.

웹 본문 Text와 이미지 OCR Text는 현재 어디서, 어떻게 합쳐지는가?

## Q3.

현재 Text 정제 기능은 어느 수준까지 구현되어 있는가?

## Q4.

RAG용 정제를 추가한다면 어느 Service/단계에 넣는 것이 가장 적절한가?

## Q5.

정제 전 Raw Text와 정제 후 Clean Text를 둘 다 저장해야 하는가?

## Q6.

현재 약 30개 의료 문서 기준으로 필요한 최소 Metadata는 무엇인가?

## Q7.

Metadata는 어떤 방식으로 입력/생성하는 것이 가장 현실적인가?

```text
수동
자동 추출
Rule
LLM
Excel/CSV
혼합
```

중 프로젝트에 맞는 방식을 제안한다.

## Q8.

현재 Neon Schema로 정제된 RAG 문서를 충분히 저장할 수 있는가?

## Q9.

DB 변경이 필요하다면 정확히 어떤 Table/Column을 최소한 수정해야 하는가?

## Q10.

현재 `document_chunks`, `chunk_embeddings`, Jina/BGE 저장 구조는 그대로 재사용 가능한가?

## Q11.

기존 RRF 검색에 DB 변경이 영향을 주는가?

## Q12.

Hugging Face Dataset이 현재 단계에서 실제로 필요한가?

## Q13.

이 기능은 현재 프로젝트 구조에서 어느 정도 작업량으로 구현 가능한가?

## Q14.

최소 구현 범위만 잡는다면 정확히 무엇만 추가하면 되는가?

---


## Q15.

현재 프로젝트 전체에서 다른 팀원이 구현한 RAG 관련 기능은 무엇이 있는가?

각 기능에 대해:

```text
파일/모듈 위치
현재 사용 여부
작성 근거(Git 이력 등, 확인 가능한 경우)
현재 RAG 탭과의 관계
재사용 가능 여부
```

를 정리한다.

## Q16.

현재 계획 중인 `정제 → Metadata → Chunk → Embedding → Neon` 과정에서
**새로 만들지 않고 기존 팀원 구현을 재사용할 수 있는 부분은 정확히 무엇인가?**

## Q17.

프로젝트 내부에 서로 다른 RAG 구현이 중복되어 있다면,
어느 구현을 기준으로 통합하는 것이 가장 안전한가?

기존 호출 관계와 현재 실제 사용 여부를 근거로 판단한다.


# 34. 최종 판단 원칙

이번 분석에서 가장 중요한 기준은 다음이다.

```text
"정제된 RAG 문서를 저장하기 위해 정말 필요한 것만 추가한다."
```

다음과 같은 과도한 방향을 피한다.

```text
전체 RAG 구조 재작성
새 Vector DB 도입
새 Framework 도입
의료 Ontology 대규모 설계
모든 Metadata 자동 AI 분류
기존 Jina/BGE/RRF 재구현
불필요한 DB 정규화
```

가능하면:

```text
현재 추출 기능
+
작은 정제 단계
+
최소 Metadata
+
기존 Chunk
+
기존 Jina/BGE
+
기존 Neon 저장
```

형태로 완성할 수 있는지를 최우선으로 검토한다.

---

# 35. 작업 종료 조건

이번 작업은 아래 조건을 만족하면 종료한다.

1. 소스코드와 DB는 변경하지 않는다.
2. 현재 RAG 적재 흐름을 실제 코드 기준으로 확인한다.
3. 정제 기능 추가 가능 위치를 특정한다.
4. DB 변경 필요 여부를 최소 범위로 판단한다.
5. 구현 가능성과 예상 작업량을 판단한다.
6. 프로젝트 전체에서 다른 팀원의 기존 RAG 관련 구현을 찾아 재사용 가능성을 분석한다.
7. 중복 구현 및 통합 위험을 확인한다.
8. 분석 보고서를 작성한다.
9. 분석 완료 후 구현을 시작하지 않고 사용자 지시를 기다린다.
