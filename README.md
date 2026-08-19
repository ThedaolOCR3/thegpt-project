# Medical AI Consultation Project

## 1. 프로젝트 소개

의료 진료 상담 AI 서비스를 목표로 개발 중인 **React + FastAPI 기반 웹 프로젝트**입니다.

현재 관리자 페이지에서는 향후 RAG 및 LLM 기능 개발을 위한 테스트 기능을 제공합니다.

- OCR 문서 분석 테스트
- VectorDB 저장 테스트
- 여러 LLM 모델 응답 비교
- React Frontend ↔ FastAPI Backend HTTP 통신

현재 OCR, LLM, Embedding, VectorDB 관련 기능은 **Mock 데이터 기반으로 동작**하며, 이후 실제 AI 기능으로 교체할 수 있도록 Router, Schema, Service를 분리해 구성했습니다.

### 주요 기술 스택

**Frontend**

- React
- TypeScript
- Vite

**Backend**

- Python
- FastAPI
- Pydantic
- Uvicorn

**향후 연동 예정**

- OCR Engine
- Ollama / LLMru
- Embedding Model
- RAG
- VectorDB

---

## 2. 실행 방법

### 동시 실행

- 프로젝트 루트의 `run.bat`을 실행합니다.
- 프론트엔드와 백엔드 api 서버만 실행하는 batch 파일입니다.
- \*\*`backend/.venv`와 `frontend/node_modules`가 이미 설치되어 있어야 합니다.

```text
run.bat
```

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

실행 후 확인:

```text
Backend      : http://localhost:8000
Swagger Docs : http://localhost:8000/docs
Health Check : http://localhost:8000/health
```

### Frontend

새 터미널에서 실행합니다.

```powershell
cd frontend
npm.cmd run dev
```

실행 후 확인:

```text
Frontend   : http://localhost:5173
Admin Page : http://localhost:5173/admin
```

Frontend의 기본 Backend API 주소는 다음과 같습니다.

```text
http://localhost:8000/api
```

`VITE_API_URL` 환경 변수를 설정하면 다른 Backend 주소를 사용할 수 있습니다.

---

## 3. 프로젝트 구조

주요 구조는 다음과 같습니다.

```text
project/
├─ frontend/
│  └─ src/
│     └─ features/
│        └─ admin/
│           └─ services/
│              ├─ adminAiService.ts
│              ├─ apiAdminAiService.ts
│              └─ mockAdminAiService.ts
│
└─ backend/
   └─ app/
      ├─ api/
      │  └─ admin/
      │     └─ router.py
      ├─ schemas/
      │  └─ admin.py
      ├─ services/
      │  ├─ admin_ocr.py
      │  └─ admin_llm.py
      └─ main.py
```

Backend는 기존 프로젝트의 다음 구조를 따릅니다.

```text
Router → Service → Repository
```

현재 Admin Mock API는 DB 접근이 필요하지 않기 때문에 별도의 Repository는 사용하지 않습니다.

각 주요 파일의 역할은 다음과 같습니다.

| 파일                                | 역할                                     |
| ----------------------------------- | ---------------------------------------- |
| `backend/app/main.py`               | FastAPI Application 진입점               |
| `backend/app/api/admin/router.py`   | Admin API Endpoint 관리                  |
| `backend/app/schemas/admin.py`      | 요청/응답 Pydantic Schema                |
| `backend/app/services/admin_ocr.py` | OCR 및 Vector 저장 테스트 처리           |
| `backend/app/services/admin_llm.py` | LLM 비교 테스트 처리                     |
| `apiAdminAiService.ts`              | Frontend에서 FastAPI 호출                |
| `adminAiService.ts`                 | Admin AI Service 연결 관리               |
| `mockAdminAiService.ts`             | Frontend 단독 테스트용 기존 Mock Service |

---

## 4. 실행 흐름

### 전체 흐름

```text
React Admin → API Service → apiClient → FastAPI Router → Service → Mock 처리 → Pydantic Response → React 결과 화면
```

현재 Service에서는 실제 AI 기능 대신 Mock 데이터를 반환합니다.

향후에는 Frontend 및 API 계약을 최대한 유지하면서 Service 내부의 Mock 처리 부분을 실제 OCR, LLM, Embedding, VectorDB 기능으로 교체하는 방식으로 확장합니다.

### OCR

```text
OcrPanel → useOcrTest → apiAdminAiService → POST /api/admin/ocr/analyze → Admin Router → analyze_document() → Mock OCR → 결과 화면
```

현재 실제 파일 본문은 전송하지 않고 파일명, 크기, Content Type, Chunk Size, Overlap 등의 메타데이터만 Backend로 전달합니다.

### VectorDB 저장 테스트

```text
OCR 결과 → POST /api/admin/ocr/vector-save-test → save_document_test() → Mock 저장 결과
```

현재는 실제 VectorDB에 데이터를 저장하지 않습니다.

### LLM 비교

```text
LlmPanel → useLlmComparison → apiAdminAiService → POST /api/admin/llm/compare → Admin Router → compare_models() → Mock LLM → 결과 비교 화면
```

현재 여러 모델의 응답 결과, 성공 여부, 응답 시간, Token 수 등을 Mock 데이터로 반환합니다.

### 향후 교체 흐름

```text
Mock OCR → 실제 OCR
Mock Vector Save → Embedding → VectorDB
Mock LLM → 실제 LLM / Ollama
문서 검색 → RAG → LLM 응답 생성
```
