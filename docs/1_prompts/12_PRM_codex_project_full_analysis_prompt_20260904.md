# Codex 지시문 — 프로젝트 전체 구조 및 흐름 분석

## 목적

현재 프로젝트 전체를 **코드 수정 없이 분석**하여 다음을 한 번에 파악한다.

- 프로젝트의 전체 디렉터리 및 모듈 구조
- Frontend / Backend / Database / OCR / RAG / LLM / Admin 기능의 연결 관계
- 사용자가 실제로 기능을 실행했을 때의 요청 흐름
- 각 기능이 어느 파일에서 시작되고 어디를 거쳐 처리되는지
- 현재 구현 완료 / 미완성 / Mock / 임시 구현 상태
- 중복 코드, 불필요한 구조, 잠재적인 오류 가능성
- 배포 및 실행 구조
- 향후 유지보수 및 팀 인수인계 시 알아야 할 핵심 내용

이번 작업은 **리팩터링이나 코드 수정 작업이 아니라 프로젝트 이해를 위한 정적 분석 작업**이다.

---

# 1. 작업 원칙

## 절대 하지 말 것

- 기존 코드 수정
- 파일 삭제
- 파일 이동
- 함수명 / 클래스명 변경
- import 정리
- 패키지 설치
- DB 데이터 수정
- migration 실행
- `.env` 값 변경
- Git commit / push
- 실제 외부 API 호출
- LLM 학습 실행
- OCR 대량 처리 실행
- 임베딩 재생성
- Neon DB 데이터 삽입 / 수정 / 삭제

필요하다면 코드와 설정 파일을 **읽기만 한다.**

---

# 2. 분석 범위

프로젝트 루트부터 전체 구조를 탐색한다.

다음 영역은 반드시 확인한다.

## Frontend

예상 기술:

- React
- TypeScript 또는 JavaScript
- Router
- API Client

확인 항목:

- `src/`
- `components/`
- `pages/`
- `layouts/`
- `services/`
- `hooks/`
- `utils/`
- `types/`
- `App.*`
- Router 설정
- 환경변수
- API 주소 설정

특히 다음 페이지와 기능을 찾아 분석한다.

- 사용자 메인 화면
- AI 상담
- 문서 업로드
- 설정
- 관리자 페이지
- Admin OCR 탭
- Admin LLM 탭

---

## Backend

예상 기술:

- FastAPI
- Python

다음 구조를 우선 확인한다.

- `app/main.py`
- `routers/`
- `services/`
- `repositories/`
- `schemas/`
- `models/`
- `core/`
- `db/`
- `utils/`
- `tests/`

다음 흐름을 확인한다.

```text
HTTP Request
→ Router
→ Service
→ Repository / AI Module
→ Database / OCR / LLM
→ Response Schema
→ Frontend
```

실제 코드가 위 구조와 다르면 실제 구조를 기준으로 설명한다.

---

# 3. 프로젝트 전체 디렉터리 구조 분석

프로젝트의 주요 디렉터리를 트리 형태로 정리한다.

단, 다음은 제외하거나 축약한다.

- `.git`
- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
- build 결과물
- cache
- model weight
- 대용량 데이터셋
- 로그 파일

예시:

```text
project-root/
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ pages/
│  │  ├─ services/
│  │  └─ ...
│  └─ ...
│
├─ backend/
│  ├─ app/
│  │  ├─ routers/
│  │  ├─ services/
│  │  ├─ repositories/
│  │  └─ ...
│  └─ ...
│
└─ docs/
```

각 디렉터리의 역할을 1~3줄 정도로 설명한다.

---

# 4. Frontend 구조 분석

다음을 확인한다.

## 4-1. 페이지 구조

각 페이지를 표로 정리한다.

| 화면 | 파일 | 주요 역할 | 호출 API |
|---|---|---|---|

예:

```text
ChatPage
→ 사용자의 의료 상담 질문 입력
→ Backend 상담 API 호출
→ 응답 출력
```

---

## 4-2. Router 구조

라우팅 구조를 분석한다.

예:

```text
BrowserRouter
→ MainLayout
   ├─ Home
   ├─ Chat
   ├─ Document
   ├─ Settings
   └─ Admin
```

실제 URL도 가능하면 같이 기록한다.

---

## 4-3. API 호출 구조

Frontend가 Backend를 호출하는 구조를 분석한다.

확인 대상:

- axios
- fetch
- apiClient
- service module
- 환경변수 기반 API URL

예:

```text
ChatPage
→ chatService
→ apiClient
→ FastAPI /api/chat
```

---

# 5. Backend API 구조 분석

등록된 FastAPI Router를 모두 확인한다.

표 형식:

| Method | Endpoint | Router | Service | 기능 |
|---|---|---|---|---|

예:

| POST | `/api/chat` | chat.py | chat_service.py | 의료 상담 |
| POST | `/api/ocr` | ocr.py | ocr_service.py | OCR 처리 |

가능하면 `main.py`에서 Router가 실제 등록되어 있는지도 확인한다.

---

# 6. 사용자 의료상담 전체 흐름

사용자가 의료 상담 질문을 입력했을 때의 전체 실행 흐름을 추적한다.

반드시 **실제 파일명과 함수명**을 포함한다.

예:

```text
[Frontend]

ChatPage
↓
chatService.sendMessage()
↓
POST /api/chat


[Backend]

chat router
↓
ChatService
↓
RAG 검색
↓
LLM 호출
↓
응답 가공
↓
Frontend 반환
```

현재 RAG가 아직 연결되지 않았거나 Mock이면 그 사실을 명확하게 표시한다.

---

# 7. OCR 구조 분석

프로젝트 내 OCR 관련 코드를 모두 검색한다.

확인할 것:

- OCR 엔진 종류
- OCR 진입점
- OCR Service
- OCR Pipeline
- 파일 업로드
- 이미지 전처리
- 텍스트 추출
- 결과 반환
- RAG 연결 여부

특히 OCR 구현이 **2곳 이상 중복되어 있는지 확인한다.**

예:

```text
OCR 구조 A
Admin OCR
→ ocr_service

OCR 구조 B
Document Upload
→ hybrid_ocr

두 구조가 동일 기능을 별도 구현하는지 확인
```

중복 구조가 있다면 다음을 정리한다.

- 각각 사용되는 위치
- 구현 차이
- 공통화 가능한 부분
- 현재 어느 쪽이 실제 서비스 경로인지

단, 코드는 수정하지 않는다.

---

# 8. RAG 구조 분석

RAG 관련 코드와 데이터 흐름을 분석한다.

확인 대상:

- 문서 입력
- OCR
- 텍스트 정제
- Chunking
- Embedding
- Vector DB 저장
- Similarity Search
- Top-K
- Prompt 삽입
- LLM 전달

전체 파이프라인을 다음 형태로 정리한다.

```text
문서 업로드
↓
OCR
↓
텍스트 추출
↓
Chunk 생성
↓
Embedding
↓
Neon PostgreSQL / pgvector
↓
질문 Embedding
↓
Vector Search
↓
Top-K Context
↓
LLM Prompt
↓
답변
```

실제 구현 여부를 단계별로 표시한다.

예:

| 단계 | 상태 | 관련 파일 |
|---|---|---|
| OCR | 구현 | xxx |
| Chunk | 구현 | xxx |
| Embedding | 구현 | xxx |
| Vector 저장 | 구현 | xxx |
| 검색 | 일부 구현 | xxx |
| LLM 연결 | 미연결 | - |

---

# 9. Embedding / Vector DB 분석

다음을 확인한다.

- Embedding 모델
- Embedding 차원
- normalize 여부
- Batch 처리 여부
- Chunk 저장 방식
- PostgreSQL 테이블
- pgvector 사용 여부
- VECTOR 차원
- similarity metric
- Top-K 설정

Neon DB와 연결된 Repository / Model 구조도 분석한다.

가능하면 아래 관계를 설명한다.

```text
Document
1
↓
N
Chunk
↓
Embedding Vector
```

---

# 10. Database 구조 분석

DB 관련 다음 항목을 확인한다.

- PostgreSQL
- Neon
- SQLAlchemy 사용 여부
- ORM Model
- Repository
- DB Session
- 환경변수
- pgvector

테이블 관계를 코드 기준으로 간단한 ERD 형태로 정리한다.

예:

```text
users
 └─ id PK

documents
 ├─ id PK
 └─ user_id FK → users.id

chunks
 ├─ id PK
 └─ document_id FK → documents.id
```

실제 DB와 코드 Model이 다를 가능성이 있으면 해당 부분도 표시한다.

---

# 11. LLM 구조 분석

프로젝트 내 LLM 호출 관련 모든 코드를 찾는다.

확인할 것:

- 사용하는 모델
- 모델 호출 방식
- Hugging Face
- Ollama
- 외부 API
- 별도 LLM Server
- FastAPI 내부 직접 호출
- HTTP 통신

다음 구조를 확인한다.

```text
Web Backend
→ LLM Service
→ Local / Remote LLM Server
→ Model
```

또는

```text
Web Backend
→ Ollama
→ Model
```

현재 실제 구조 기준으로 설명한다.

---

# 12. Prompt 구조 분석

의료 상담 Prompt 관련 파일을 찾는다.

예:

```text
medical_prompts.py
```

다음을 확인한다.

- Prompt Version
- System Prompt
- User Prompt Template
- 응답 형식
- 안전성 규칙
- 응급상황 처리
- RAG Context 삽입 위치

가능하면 다음 형태로 설명한다.

```text
System Prompt
+
RAG Context
+
User Question
↓
LLM
```

---

# 13. Fine-tuning 모델 연결 여부

프로젝트 코드에서 다음 모델 또는 Adapter가 실제 연결되어 있는지 확인한다.

- MedGemma
- Gemma
- Qwen3
- Llama
- LoRA / QLoRA Adapter

다음처럼 구분한다.

| 모델 | 학습 여부 | 프로젝트 연결 | 실제 호출 가능 여부 |
|---|---|---|---|

학습 결과 파일만 존재하고 실제 웹서비스에 연결되지 않았다면 이를 분리해서 설명한다.

---

# 14. Admin 페이지 구조 분석

Admin 페이지는 별도 항목으로 자세히 분석한다.

## OCR Tab

확인:

- 문서 업로드
- OCR 테스트
- OCR 엔진 선택
- Chunk
- Embedding
- Vector DB 저장
- 처리 결과 표시

---

## LLM Tab

확인:

- 모델 목록
- 단일 모델 실행
- 전체 모델 비교 실행
- 실행 취소
- 응답 시간
- Token 사용량
- 결과 비교

다음 모델 비교 목적이 코드에서 어떻게 표현되어 있는지 확인한다.

- 최종 학습 모델
- 학습이 덜 된 모델
- 다른 Base 모델
- LoRA Adapter 모델

Mock 데이터가 있다면 실제 API와 구분해서 표시한다.

---

# 15. Mock / Dummy / 임시 코드 탐색

프로젝트 전체에서 다음 키워드를 검색한다.

```text
mock
dummy
sample
temp
todo
fixme
placeholder
hardcoded
test data
```

또한 코드상 의미가 유사한 임시 구현도 찾아본다.

결과를 표로 정리한다.

| 파일 | 내용 | 실제 서비스 영향 |
|---|---|---|

---

# 16. 중복 코드 분석

프로젝트 전체에서 기능 중복 가능성을 확인한다.

특히:

- OCR
- API Client
- DB Session
- LLM 호출
- Prompt
- Embedding
- 파일 업로드
- Admin API
- 사용자 API

중복이 있다면 다음을 설명한다.

```text
기능
├─ 구현 A
└─ 구현 B

차이:
A:
B:

현재 사용:
A / B / 둘 다

문제 가능성:
...
```

코드 수정은 하지 않는다.

---

# 17. 환경변수 분석

`.env.example`, config 관련 파일 등을 확인한다.

실제 비밀값은 출력하지 않는다.

다음처럼 **변수명만 정리**한다.

```text
DATABASE_URL
LLM_API_URL
OPENAI_API_KEY
GOOGLE_API_KEY
...
```

각 환경변수가 어떤 코드에서 사용되는지도 연결한다.

---

# 18. Docker 구조 분석

다음을 확인한다.

- Dockerfile
- docker-compose
- Frontend Container
- Backend Container
- DB 외부 연결
- Port
- Volume
- 환경변수

실행 구조를 예로 설명한다.

```text
Browser
↓
Frontend
↓
Backend
↓
Neon

Backend
↓
LLM Server
```

현재 Docker로 실제 전체 서비스 실행이 가능한지도 판단한다.

---

# 19. 배포 구조 분석

다음 항목을 검색한다.

- Cloudflare
- Workers
- Tunnel
- deployment
- production URL
- dev URL
- CI/CD
- GitHub Actions

가능하면 다음 관계를 정리한다.

```text
GitHub dev branch
↓
배포
↓
Cloudflare
↓
Web Service
```

실제 코드/설정에서 확인되지 않는 내용은 추측하지 않는다.

---

# 20. 테스트 구조 분석

다음을 확인한다.

- unit test
- integration test
- API test
- pytest
- frontend test

표:

| 테스트 파일 | 대상 기능 | 테스트 종류 | 실행 가능 여부 |
|---|---|---|---|

테스트 코드가 존재하지만 실제 기능 변경으로 깨졌을 가능성도 확인한다.

---

# 21. 실제 실행 흐름 5개 추적

다음 기능은 반드시 처음부터 끝까지 호출 흐름을 추적한다.

## A. 사용자 의료 상담

```text
Frontend
→ API
→ Backend
→ RAG
→ LLM
→ Response
```

## B. 문서 업로드

```text
Frontend
→ Upload API
→ OCR
→ Chunk
→ Embedding
→ Vector DB
```

## C. Admin OCR 테스트

```text
Admin
→ OCR API
→ OCR Engine
→ Result
```

## D. Admin LLM 비교

```text
Admin
→ LLM Test API
→ 각 Model
→ Result Compare
```

## E. 사용자 인증 / Admin 권한

```text
Login
→ User
→ is_admin
→ Admin 접근
```

구현되지 않은 단계는 임의로 채우지 말고 `미구현`이라고 표시한다.

---

# 22. 프로젝트 상태 분류

기능별로 다음 5개 상태 중 하나로 분류한다.

```text
완료
대부분 완료
부분 구현
Mock / 임시
미구현
```

표:

| 기능 | 상태 | 판단 근거 |
|---|---|---|

대상:

- 사용자 UI
- 상담 API
- OCR
- RAG
- Embedding
- Vector DB
- LLM
- Prompt
- Admin OCR
- Admin LLM
- DB
- 인증
- Docker
- 배포
- 테스트

---

# 23. 문제 및 위험요소 분석

다음 등급으로 구분한다.

## Critical

서비스 실행 또는 데이터에 직접 영향을 주는 문제

## High

기능 오류 가능성이 높은 문제

## Medium

유지보수 또는 구조 개선 필요

## Low

정리하면 좋은 수준

형식:

| 등급 | 문제 | 관련 파일 | 영향 |
|---|---|---|---|

---

# 24. 발표 / 포트폴리오 관점 정리

프로젝트를 처음 보는 사람이 이해할 수 있도록 기술적으로 설명한다.

다음 내용을 포함한다.

## 프로젝트 한 줄 설명

예:

> 의료 문서 OCR 및 RAG 기반 의료 상담을 제공하는 LLM 웹 서비스

실제 구현을 기준으로 수정한다.

---

## 핵심 기술

예:

```text
Frontend
- React

Backend
- FastAPI

Database
- PostgreSQL / Neon
- pgvector

AI
- OCR
- Embedding
- RAG
- LLM
- QLoRA Fine-tuning

Infra
- Docker
- Cloudflare
```

---

## 핵심 서비스 흐름

```text
사용자 질문
↓
FastAPI
↓
RAG
↓
Vector DB
↓
LLM
↓
의료 상담 답변
```

---

# 25. 신규 개발자가 꼭 알아야 할 파일

프로젝트에서 가장 중요한 파일 10~20개를 선정한다.

표:

| 순위 | 파일 | 이유 |
|---|---|---|

예:

```text
1. backend/app/main.py
2. backend/app/routers/chat.py
3. backend/app/services/chat_service.py
...
```

---

# 26. 현재 프로젝트에서 가장 중요한 기술적 포인트

분석 마지막에는 반드시 다음 질문에 답한다.

1. 이 프로젝트의 핵심 Backend 진입점은 어디인가?
2. 의료 상담은 어떤 API에서 시작되는가?
3. LLM은 어디에서 호출되는가?
4. RAG는 실제 서비스에 연결되어 있는가?
5. OCR은 몇 개의 구현이 존재하는가?
6. Embedding은 어떤 모델을 사용하는가?
7. Vector DB는 어디에 저장되는가?
8. Admin OCR과 사용자 OCR은 같은 Pipeline을 사용하는가?
9. Admin LLM 비교 기능은 실제 모델 호출인가 Mock인가?
10. Docker 실행 시 어떤 서비스가 올라오는가?
11. Cloudflare 배포 구조는 어떻게 되어 있는가?
12. 현재 가장 큰 기술적 위험요소는 무엇인가?
13. 지금 제거해도 되는 Mock / 임시 코드는 무엇인가?
14. 지금 프로젝트를 다른 개발자가 넘겨받으면 가장 먼저 봐야 할 파일은 무엇인가?
15. 발표에서 설명할 때 가장 단순한 전체 아키텍처는 어떻게 표현하면 되는가?

---

# 27. 최종 보고서 작성

분석 결과를 다음 파일로 작성한다.

```text
docs/15_프로젝트_전체구조분석_20260904.md
```

해당 번호가 이미 사용 중이면 기존 문서를 덮어쓰지 말고 다음 번호를 사용한다.

예:

```text
15_...
16_...
17_...
```

---

# 28. 보고서 권장 목차

```markdown
# 프로젝트 전체 구조 분석

## 1. 프로젝트 개요

## 2. 전체 디렉터리 구조

## 3. 전체 시스템 아키텍처

## 4. Frontend 구조

## 5. Backend 구조

## 6. API 목록

## 7. 의료 상담 실행 흐름

## 8. OCR 구조

## 9. RAG 구조

## 10. Embedding / Vector DB 구조

## 11. Database 구조

## 12. LLM 구조

## 13. Prompt 구조

## 14. Fine-tuning 모델 연결 상태

## 15. Admin 구조

## 16. Docker / 배포 구조

## 17. 테스트 구조

## 18. Mock / 임시 코드

## 19. 중복 구현

## 20. 기능별 구현 상태

## 21. 문제 및 위험요소

## 22. 중요 파일 목록

## 23. 신규 개발자용 프로젝트 이해 순서

## 24. 발표 / 포트폴리오용 요약

## 25. 최종 결론
```

---

# 29. 분석 작성 규칙

## 코드 근거 우선

설명은 추측보다 실제 코드를 우선한다.

가능하면 설명마다 관련 파일을 표시한다.

예:

```text
backend/app/services/chat_service.py

ChatService.generate_response()
```

---

## 불확실하면 명확히 표시

다음 표현을 사용한다.

```text
확인됨
추정
미확인
미구현
Mock
사용되지 않는 것으로 보임
```

추측을 사실처럼 작성하지 않는다.

---

## 실행 경로 중심으로 설명

단순히 파일 목록을 나열하지 말고 다음 관점으로 분석한다.

```text
사용자 행동
↓
Frontend
↓
API
↓
Backend
↓
Service
↓
AI / DB
↓
Response
```

---

# 30. 마지막에 별도 요약 출력

보고서 작성 후 터미널 또는 Codex 응답에는 다음 내용만 간단히 정리한다.

## 프로젝트 구조

```text
Frontend:
Backend:
Database:
OCR:
RAG:
LLM:
Deployment:
```

## 현재 상태

```text
완료:
부분 구현:
Mock:
미구현:
```

## 가장 중요한 문제 TOP 5

1.
2.
3.
4.
5.

## 지금 프로젝트를 이해하기 위해 먼저 볼 파일 TOP 10

1.
2.
3.
4.
5.
6.
7.
8.
9.
10.

---

# 핵심 지시

이번 작업의 목적은 **프로젝트 전체를 처음 보는 개발자가 하나의 보고서만 읽고도 구조와 실행 흐름을 이해할 수 있도록 만드는 것**이다.

단순 파일 나열이 아니라 반드시 다음 연결 관계를 중심으로 분석한다.

```text
React Frontend
      ↓
FastAPI Backend
      ↓
Service Layer
 ┌────┼──────────┐
 ↓    ↓          ↓
OCR   RAG       LLM
      ↓
Embedding
      ↓
Neon PostgreSQL / pgvector
```

단, 위 그림은 예시다.

**반드시 실제 프로젝트 코드 구조를 확인한 뒤 실제 구조에 맞춰 최종 아키텍처를 작성한다.**

코드는 수정하지 않는다.
분석과 문서 작성만 수행한다.
