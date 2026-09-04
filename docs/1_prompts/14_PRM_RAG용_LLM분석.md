# RAG 질의응답 구조 분석 및 최소 테스트 설계 지시문

## 1. 작업 목적

현재 프로젝트에는 RAG 기능이 이미 구현되어 있다.

향후 별도의 테스트용 브랜치에서 다음 형태의 테스트를 수행하려고 한다.

```text
고정 질문 약 5개
→ 질문 Embedding
→ 기존 Neon Vector DB 검색
→ Top-K 문서/Chunk 조회
→ RAG Context 생성
→ 지정 Prompt 적용
→ MedGemma + LoRA Adapter 질의
→ 결과 TXT / JSONL 저장
```

이번 작업의 목적은 **새로운 RAG를 구현하는 것이 아니라**,
현재 dev 프로젝트의 실제 RAG 구조를 분석하여
기존 코드를 최대한 재사용하는 최소 테스트 실행 파일을 설계하는 것이다.

---

# 2. 매우 중요한 작업 제한

이번 단계에서는 **분석만 수행한다.**

다음 작업은 절대 하지 않는다.

- 기존 코드 수정
- 새로운 Python 파일 구현
- DB INSERT
- DB UPDATE
- DB DELETE
- 새로운 문서 저장
- 새로운 Chunk 저장
- 새로운 문서 Embedding 저장
- 테스트 질문 저장
- 실제 RAG 테스트 실행
- 실제 LLM 실행
- 리팩터링
- 패키지 설치
- 환경변수 수정

특히 Neon DB는 사용량 기반 비용이 발생할 수 있으므로
**DB에 데이터를 쓰는 작업은 절대 실행하지 않는다.**

현재 코드만 읽어서 분석한다.

---

# 3. 최종 테스트 목표

향후 만들 테스트 파일은 대략 다음 역할만 수행해야 한다.

```text
질문
↓
질문 Embedding 생성
↓
기존 Neon DB Vector 검색
↓
Top-K Context 조회
↓
RAG Prompt 구성
↓
LLM 추론
↓
로컬 파일 저장
```

중요:

```text
질문 Embedding
→ 검색에만 사용
→ DB에 저장하지 않음

검색 결과
→ 조회만 수행
→ DB에 다시 저장하지 않음

LLM 응답
→ Neon 저장하지 않음
→ 로컬 TXT / JSONL 저장
```

---

# 4. RAG 전체 실행 흐름 분석

현재 프로젝트에서 실제 RAG 흐름을 코드 기준으로 추적한다.

아래 흐름이 어떻게 구현되어 있는지 확인한다.

```text
사용자 질문
→ API / Service
→ Embedding 생성
→ Vector DB 검색
→ Top-K 결과 반환
→ Context 구성
→ Prompt 구성
→ LLM 호출
→ 응답 반환
```

각 단계별로 다음 항목을 기록한다.

| 항목      | 내용               |
| --------- | ------------------ |
| 파일 경로 | 실제 코드 경로     |
| 클래스    | 존재할 경우        |
| 함수      | 실제 함수명        |
| 입력      | parameter / object |
| 반환      | return type / 구조 |
| 다음 호출 | 다음 단계 함수     |

추측하지 말고 실제 코드만 기준으로 작성한다.

---

# 5. 질문 Embedding 구조 분석

다음을 확인한다.

- 사용 중인 Embedding 모델명
- Embedding 모델을 로드하는 파일
- Embedding Service / 함수
- 질문 Embedding 생성 함수
- 문서 Embedding 생성 함수
- 질문과 문서가 동일 모델을 사용하는지
- Embedding dimension
- normalize 여부
- batch 처리 여부

특히 다음 질문에 명확히 답한다.

> 사용자 질문의 Embedding vector를 생성한 뒤
> Neon DB에 저장하는가,
> 아니면 Vector 검색에만 사용하고 폐기하는가?

코드 근거를 함께 기록한다.

---

# 6. Neon / Vector DB 구조 분석

RAG에서 실제 사용하는 Neon DB 구조를 확인한다.

다음을 조사한다.

- RAG 관련 테이블명
- Document 관련 테이블
- Chunk 관련 테이블
- Embedding 저장 컬럼
- vector dimension
- primary key
- document_id / chunk_id 관계
- source
- title
- url
- metadata
- created_at
- similarity 관련 값

실제 프로젝트에 없는 필드는 작성하지 않는다.

가능하면 현재 코드에서 사용하는 ORM Model 또는 SQL 구조를 기준으로 표로 정리한다.

---

# 7. Vector 검색 Query 분석

현재 질문과 유사한 Chunk를 찾는 실제 Query를 찾는다.

다음을 확인한다.

- pgvector 사용 여부
- cosine distance / inner product / L2 등 사용 방식
- 실제 연산자
- Top-K
- threshold
- score 계산
- ORDER BY
- LIMIT
- 문서별 중복 제거
- Chunk 필터링
- metadata 필터링

실제 Query 또는 ORM 코드를 발췌하여 설명한다.

예시는 만들지 않는다.

---

# 8. Retrieval 결과 구조 분석

Vector 검색 후 반환되는 실제 데이터 구조를 확인한다.

예를 들어 다음과 같은 값 중 실제로 어떤 것이 존재하는지 확인한다.

```text
content
chunk_text
document_id
chunk_id
source
title
url
similarity
distance
score
metadata
```

가능하면 실제 반환 형태를 아래처럼 표현한다.

```json
{
  "실제필드": "..."
}
```

단, 실제 코드에 없는 필드는 추가하지 않는다.

---

# 9. Context 구성 과정 분석

검색된 Top-K 결과가 LLM에 전달되기 전에
어떻게 Context로 조립되는지 확인한다.

다음을 조사한다.

- Context 생성 함수
- Chunk 여러 개를 합치는 방식
- 구분 문자열
- source 포함 여부
- metadata 포함 여부
- 최대 Context 길이
- token 제한
- 중복 제거 여부
- Context 없는 경우 처리

특히 최종적으로 LLM이 받는 문자열 또는 message 구조를 보여준다.

---

# 10. Prompt 적용 구조 분석

현재 프로젝트에서 System Prompt 또는 RAG Prompt를 어디에서 적용하는지 확인한다.

다음을 정리한다.

- Prompt 파일 위치
- Prompt 상수 위치
- Prompt 로딩 함수
- system / user message 구성
- RAG Context 삽입 위치
- 사용자 질문 삽입 위치
- chat template 적용 여부

현재 프로젝트에서 Prompt가 아직 임시 구현이거나
RAG와 LLM 연결이 미완성이라면 그대로 기록한다.

추측해서 구조를 완성하지 않는다.

---

# 11. LLM 호출 구조 분석

다음을 확인한다.

- LLM 호출 파일
- Service
- 중심 함수
- API 사용 여부
- 로컬 모델 여부
- 현재 Base Model
- Adapter 사용 여부
- request / response 구조
- Generation 설정 위치

현재 프로젝트의 LLM이
향후 별도의 MedGemma 테스트 실행 파일로 대체될 예정이라면
RAG에서 LLM으로 넘기는 **최소 입력값만** 정리한다.

---

# 12. DB Write / DB Read 완전 분리

RAG 관련 함수들을 아래 세 종류로 분류한다.

## A. DB Write

예:

```text
문서 INSERT
Chunk INSERT
Embedding INSERT
UPDATE
DELETE
```

## B. DB Read

예:

```text
Vector similarity SELECT
Document 조회
Chunk 조회
metadata 조회
```

## C. DB와 무관

예:

```text
질문 Embedding 생성
Context 생성
Prompt 생성
LLM 호출
결과 파일 저장
```

다음 형태의 표를 작성한다.

| 함수 | 파일 | 종류  | 테스트에서 사용 여부 |
| ---- | ---- | ----- | -------------------- |
| ...  | ...  | READ  | 사용                 |
| ...  | ...  | WRITE | 사용 금지            |

---

# 13. 테스트에서 절대 호출하면 안 되는 함수

Neon 저장량 증가 가능성이 있는 함수들을 별도로 목록화한다.

예:

```text
save_document()
save_chunks()
save_embedding()
upsert_xxx()
insert_xxx()
```

실제 프로젝트에 존재하는 함수만 작성한다.

향후 테스트 실행 파일에서는
이 함수들을 호출하지 않아야 한다.

---

# 14. 기존 코드 중 재사용 가능한 최소 모듈

향후 별도의 테스트 실행 파일:

```text
rag_prompt_eval.py
```

하나를 만든다고 가정한다.

이 파일에서 기존 프로젝트의 어떤 모듈을 import하면 되는지 분석한다.

목표는 중복 구현을 최소화하는 것이다.

가능하면 다음처럼 정리한다.

```python
from app.xxx import ...
from app.xxx import ...
from app.xxx import ...
```

단, 실제 import 가능 여부를 확인한다.

필요한 구성요소 후보:

```text
Config
DB Connection
Embedding Service
Vector Repository
Retrieval Service
Context Builder
```

---

# 15. 최소 테스트 실행 구조 설계

아직 코드는 작성하지 않는다.

향후 실행 파일의 권장 흐름만 작성한다.

예:

```text
main()
│
├─ 환경 설정 로드
├─ DB 연결
├─ Embedding 모델 준비
├─ MedGemma + Adapter 로드
│
├─ 고정 질문 5개 반복
│   ├─ 질문 Embedding
│   ├─ Neon Vector SELECT
│   ├─ Top-K Context
│   ├─ 지정 Prompt
│   ├─ MedGemma generate
│   └─ 결과 저장
│
└─ 종료
```

---

# 16. Retrieval Snapshot 설계

향후 프롬프트 V4.1 / V4.2를 공정하게 비교하기 위해
첫 검색 결과를 로컬 JSON으로 저장할 예정이다.

예상 흐름:

```text
첫 테스트
질문
→ 실제 Neon 검색
→ Top-K
→ retrieval_snapshot.json 저장

두 번째 테스트
Neon 검색 없이
→ 동일 Snapshot 사용
→ 다른 Prompt로 LLM 실행
```

현재 Retrieval 결과 구조를 기준으로
Snapshot에 저장해야 할 최소 필드를 제안한다.

예:

```text
question_id
question
chunk_id
content
source
score
```

단, 실제 Retrieval 결과에 존재하는 필드만 사용한다.

---

# 17. 로컬 결과 저장 설계

향후 테스트 결과는 DB가 아니라 로컬 파일에 저장한다.

예:

```text
outputs/
  rag_v4.1_result.txt
  rag_v4.1_debug.jsonl
  retrieval_snapshot.json
```

TXT에는 사람이 읽을 수 있는 결과를 기록한다.

예:

```text
Question
Retrieved Context
Final Answer
Elapsed Time
```

JSONL에는 분석용 metadata를 기록한다.

예:

```text
question_id
retrieval count
retrieval score
generated_tokens
stop_reason
elapsed_seconds
```

현재 코드에서 실제 확보 가능한 값 기준으로 설계한다.

---

# 18. 질문 5개 테스트 시 예상 DB 영향 분석

다음 조건을 가정한다.

```text
새 문서 저장 없음
새 Chunk 저장 없음
문서 Embedding 저장 없음
질문 Embedding 저장 없음
답변 저장 없음

질문 Embedding 생성
+
기존 Neon Vector SELECT
```

이 경우:

- Neon Storage가 증가하는지
- Compute / Query 사용량만 발생하는지
- 어떤 코드 때문에 Storage가 증가할 가능성이 있는지

현재 코드 기준으로 설명한다.

확실하지 않은 경우:

```text
확인 필요
```

라고 표시한다.

---

# 19. 환경 의존성 확인

테스트 브랜치에서 실행하기 위해 필요한 환경을 조사한다.

다음을 정리한다.

- 필수 `.env` 항목 이름
- Neon connection 관련 환경 변수
- Embedding model 관련 환경 변수
- Hugging Face 관련 설정
- 필요한 Python package
- 실행 위치
- PYTHONPATH 문제 가능성
- async 환경 여부

환경변수의 실제 비밀번호나 Secret 값은 출력하지 않는다.

변수 이름만 기록한다.

---

# 20. 위험 요소

최소 테스트 파일을 만들 때 예상되는 위험을 정리한다.

예:

```text
Embedding dimension 불일치
Embedding 모델 불일치
Async DB session 문제
기존 Application context 의존
환경 변수 누락
Neon connection pool
RAG 검색 함수 내부의 예상치 못한 DB Write
LLM Context 길이 초과
```

각 위험마다 간단한 확인 방법을 적는다.

---

# 21. 최종 판단

분석 마지막에 다음 질문에 답한다.

### Q1.

현재 프로젝트 코드만 재사용해서
`rag_prompt_eval.py` 하나로 테스트 가능한가?

```text
가능
부분적으로 가능
어려움
```

중 하나로 판단한다.

### Q2.

별도의 RAG 시스템을 다시 구현해야 하는가?

### Q3.

DB Write 없이 기존 Neon 데이터만 조회할 수 있는가?

### Q4.

질문 Embedding은 DB에 저장하지 않고 검색에만 사용할 수 있는가?

### Q5.

고정 질문 5개 테스트를 수행할 때
Neon Storage 증가를 최소화할 수 있는가?

### Q6.

다음 구현 단계에서 수정하거나 추가해야 할 최소 파일은 무엇인가?

---

# 22. 최종 산출물

다음 Markdown 문서 하나만 작성한다.

```text
RAG_구조분석_및_최소질의테스트_설계.md
```

문서 구성:

```text
1. 전체 RAG 구조 요약
2. 실제 실행 흐름
3. 주요 파일 및 함수
4. Embedding 구조
5. Neon / Vector DB 구조
6. Retrieval Query
7. Top-K 및 검색 설정
8. Retrieval 반환 구조
9. Context 구성
10. Prompt / LLM 연결
11. DB Write / Read 구분
12. 테스트에서 금지할 함수
13. 재사용 가능한 모듈
14. 최소 rag_prompt_eval.py 설계
15. Retrieval Snapshot 설계
16. 로컬 결과 저장 설계
17. 예상 DB 사용량 영향
18. 필요한 환경 설정
19. 위험 요소
20. 다음 단계 구현 권장안
```

---

# 핵심 원칙

이번 분석의 목표는:

> **“RAG를 새로 구현하는 것”이 아니라,
> 현재 dev 프로젝트의 RAG 코드를 최대한 재사용하여
> DB Write 없이 대표 질문 5개를 테스트할 수 있는
> 최소 실행 구조를 파악하는 것**

이다.

이번 단계에서는 실제 구현이나 실행을 하지 않는다.
