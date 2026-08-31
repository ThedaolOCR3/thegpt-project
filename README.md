# Medical AI Consultation Project

의료 진료 상담 AI 서비스를 목표로 개발 중인 **React + FastAPI 기반 웹 프로젝트**입니다.

관리자 페이지에서 문서 OCR, 청크 설정, Jina v4·Medical BGE-M3 이중 Embedding 기반 VectorDB 저장, LLM 응답 비교 기능을 제공합니다. 메인 페이지에서는 두 Dense 검색 순위를 RRF로 합친 의료 RAG와 공통 Model Registry의 LLM을 사용합니다. PDF와 이미지뿐 아니라 DOCX/PPTX도 처리하며, Office 문서는 LibreOffice 없이 OOXML을 직접 추출합니다.

## 1. 주요 기술 스택

### Frontend

- React
- TypeScript
- Vite

### Backend

- **Python 3.12**
- FastAPI / Pydantic / Uvicorn
- SQLAlchemy / Alembic / PostgreSQL(pgvector)
- PaddleOCR / PyMuPDF
- python-docx / python-pptx

## 2. 최초 설정(개발자 수동 실행)

`run.bat`은 서버 실행만 담당합니다. 최초 1회는 아래 설치와 환경 설정을 개발자가 직접 완료해야 합니다.

### 2.1 필수 프로그램

- Windows 10/11
- Git
- **Python 3.12.x 64-bit**
- Node.js와 npm

이 프로젝트의 Backend 가상환경은 반드시 Python 3.12로 생성합니다. 다른 Python 버전으로 만든 가상환경은 사용하지 않습니다.

PowerShell에서 설치 상태를 확인합니다.

```powershell
py -3.12 --version
node --version
npm.cmd --version
```

`py -3.12` 명령이 동작하지 않으면 Python 3.12를 먼저 설치하고 Python Launcher를 활성화한 뒤 진행합니다.

### 2.2 저장소 준비

```powershell
git clone <repository-url>
cd thegpt-project
```

이미 저장소를 받은 경우 프로젝트 최상위 디렉터리에서 다음 단계부터 진행합니다.

### 2.3 Backend 가상환경 및 패키지 설치

프로젝트 최상위 디렉터리에서 실행합니다.

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

설치된 Python 버전을 반드시 확인합니다.

```powershell
backend\.venv\Scripts\python.exe --version
```

출력은 `Python 3.12.x`여야 합니다..

일반적인 최초 설정은 `backend/requirements.txt` 하나만 설치하면 됩니다. 개발 도구도 이 파일에 통합되어 있습니다. 기존 협업 흐름에서 `requirements-dev.txt`를 사용하던 팀원은 해당 파일을 그대로 설치해도 동일하게 동작합니다.

### 2.4 Frontend 패키지 설치

```powershell
cd frontend
npm.cmd install
cd ..
```

Windows PowerShell 실행 정책 때문에 `npm`이 차단되는 환경에서는 위와 같이 `npm.cmd`를 사용합니다.

### 2.5 환경 변수 설정

프로젝트는 최상위 `.env` 하나를 사용합니다. 최초 설정 때 예제 파일을 복사한 뒤 실제 개발 환경 값으로 수정합니다.

```powershell
Copy-Item .env.example .env
```

최소한 데이터베이스 연결 정보 등 실행에 필요한 값을 확인합니다.

```dotenv
DATABASE_URL=postgresql+psycopg://...
```

`.env`에는 비밀 정보가 포함될 수 있으므로 Git에 커밋하지 않습니다. 이미 `.env`가 존재하면 복사 명령으로 덮어쓰지 말고 기존 파일을 사용합니다.

### 2.6 데이터베이스 마이그레이션

연결할 데이터베이스를 준비하고 최상위 `.env`를 설정한 다음 실행합니다.

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

## 3. 최초 설정 이후 실행

최초 설정이 끝난 뒤에는 프로젝트 최상위에서 `run.bat` 한 번만 실행하면 Backend와 Frontend가 각각 새 터미널에서 시작됩니다.

```powershell
.\run.bat
```

또는 파일 탐색기에서 `run.bat`을 더블 클릭합니다.

`run.bat`은 다음 항목을 점검한 후 서버를 실행합니다.

- 최상위 `.env` 존재 여부
- `backend/.venv` 존재 여부와 Python 3.12 사용 여부
- Backend 핵심 패키지 설치 여부
- Node.js/npm 및 `frontend/node_modules` 존재 여부

실행 주소:

```text
Frontend     : http://localhost:5173
Admin Page   : http://localhost:5173/admin
Backend      : http://localhost:8000
Swagger Docs : http://localhost:8000/docs
Health Check : http://localhost:8000/health
DB Health    : http://localhost:8000/health/db
```

종료할 때는 Backend와 Frontend 터미널에서 각각 `Ctrl+C`를 누르거나 해당 터미널 창을 닫습니다.

> `requirements.txt` 또는 `package.json`이 변경된 경우에는 `run.bat`이 패키지를 자동 설치하지 않습니다. 개발자가 각각 `pip install -r backend\requirements.txt`, `npm.cmd install`을 다시 실행해야 합니다.

## 4. 서버 개별 실행

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Frontend

새 터미널에서 실행합니다.

```powershell
cd frontend
npm.cmd run dev
```

Frontend의 기본 Backend API 주소는 `http://localhost:8000/api`입니다. 다른 주소를 사용하려면 최상위 `.env`의 `VITE_API_URL`을 설정합니다. Vite는 `frontend/vite.config.ts`의 `envDir` 설정으로 최상위 환경 파일을 읽으며 브라우저에는 `VITE_` 접두사 변수만 노출합니다.

## 5. 주요 프로젝트 구조

```text
thegpt-project/
├─ .env                         # 로컬 통합 환경 변수(Git 제외)
├─ .env.example                 # 환경 변수 예제
├─ run.bat                      # 최초 설정 이후 통합 실행
├─ backend/
│  ├─ .venv/                    # Python 3.12 가상환경(Git 제외)
│  ├─ requirements.txt          # Backend 전체 의존성의 단일 기준
│  ├─ requirements-dev.txt      # 기존 팀원의 개발환경 설치 파일
│  └─ app/
│     ├─ api/                   # FastAPI Router
│     ├─ schemas/               # 요청/응답 Schema
│     └─ services/
│        ├─ hybrid_ocr/         # PDF/이미지/DOCX/PPTX 처리
│        └─ llm/                # Provider 계약, 모델 Registry, 실제/Mock 실행
├─ frontend/
│  ├─ package.json
│  └─ src/
│     └─ features/admin/        # 관리자 OCR/LLM 테스트 UI
└─ docs/                        # 구현 보고서, 구조 흐름, 오류 문서
```

## 6. OCR 처리 개요

관리자 OCR 화면은 파일을 비동기 작업으로 등록하고 상태를 조회합니다.

```text
React Admin
  → POST /api/admin/ocr/jobs
  → OCR Job Manager
  → 문서 검증
  → 형식별 추출
      ├─ PDF: Native Text + 필요한 페이지만 OCR
      ├─ PNG/JPG: PaddleOCR
      ├─ DOCX: python-docx 직접 추출
      └─ PPTX: python-pptx 직접 추출
  → 텍스트 정리 및 Chunk 생성
  → GET /api/admin/ocr/jobs/{jobId}
  → 결과 화면
  → POST /api/admin/ocr/vector-save
  → Vast.ai Jina v4 + Medical BGE-M3 (1024차원)
  → Neon admin_documents + document_chunks + chunk_embeddings Transaction 저장
```

OCR 전체 구조와 Office 직접 추출 전환 내용은 다음 문서를 참고합니다.

- `docs/3_flow/05_FLW_OCR_전체구조흐름_20260820.md`
- `docs/2_reports/06_RPT_OCR_Office직접추출전환_20260820.md`

현재 OCR은 실제 문서를 처리하며, 완료된 OCR Job의 Chunk를 Vast.ai의 Jina/BGE 두 Provider로 임베딩해 Neon `chunk_embeddings` 테이블에 저장합니다. 사용자 질문도 같은 두 Provider로 변환하고 각각의 pgvector Top 20 순위를 RRF로 합쳐 메인 상담 LLM Context로 사용합니다. 어드민 LLM 비교와 메인 상담 채팅은 Gemma, MedGemma 최종·데이터셋, Qwen, Llama의 실제 모델 5개를 공유하며 Gemini LLM은 사용하지 않습니다.

원본 파일 저장소는 이번 범위에 포함하지 않습니다. `admin_documents.original_file_url`의 `NOT NULL` 계약을 지키기 위해 실제 파일 URL과 구분되는 `ocr-job://...` 추적 참조값을 저장합니다.

## 7. LLM Provider 설정

어드민과 메인 상담 LLM은 Vast.ai의 2× Tesla V100 서버에 올린 다음 5개 모델을 공통으로 호출합니다.

- `gemma`: `ghddls7799/gemma-2-2b-med-ko-qlora`
- `medgemma`: 최종 `gon-0130/medgemma-4b-lora-consultation-main-v2`
- `medgemma-dataset`: 데이터셋 `gon-0130/medgemma-4b-lora-consultation`
- `qwen`: `csj9630/qwen3-4b-medical-qlora`
- `llama`: `csj9630/llama32-3b-medical-qlora`

Vast.ai에서는 `scripts/vastai_medical_llm_server.ipynb`를 프로젝트 루트에서 실행합니다. 모델은 프로젝트의 `models/`에 저장되고 Git에서는 제외됩니다. GPU 0은 FP16 Gemma/Qwen/Llama, GPU 1은 FP32 MedGemma를 담당하며 MedGemma 두 LoRA는 하나의 base를 공유합니다.

최상위 `.env`에서 Provider를 설정합니다.

```dotenv
LLM_REMOTE_ENABLED=true
LLM_REMOTE_BASE_URL=http://Vast_호스트:공개포트
LLM_REMOTE_API_KEY=Vast_서버와_공유한_Bearer_키
LLM_REMOTE_GEMMA_MODEL=gemma
LLM_REMOTE_MEDGEMMA_FINAL_MODEL=medgemma-final
LLM_REMOTE_MEDGEMMA_DATASET_MODEL=medgemma-dataset
LLM_REMOTE_QWEN_MODEL=qwen
LLM_REMOTE_LLAMA_MODEL=llama
LLM_REMOTE_MAX_CONCURRENCY=5

EMBEDDING_REMOTE_BASE_URL=https://Vast_Embedding_호스트
EMBEDDING_API_KEY=Vast_Embedding_서버와_공유한_Bearer_키
EMBEDDING_JINA_MODEL=jina-v4
EMBEDDING_BGE_MODEL=medical-bgem3
EMBEDDING_DIMENSION=1024
EMBEDDING_TIMEOUT_SECONDS=60
EMBEDDING_BATCH_SIZE=32
RAG_EMBEDDING_PROVIDER=remote_dual
```

`EMBEDDING_REMOTE_BASE_URL`에는 `/v1/embeddings`를 붙이지 않습니다. `EMBEDDING_API_KEY`와 `LLM_REMOTE_API_KEY`는 Backend에서만 사용하며 `VITE_` 접두사를 붙이지 않고 Git에 커밋하지 않습니다.

Jina v4는 기본 dense 출력이 2048차원이므로 Vast.ai 서버에서 `task="retrieval"`, `truncate_dim=1024`, `prompt_name="query"` 또는 `"passage"`를 적용해야 합니다. Backend는 두 모델의 모델명·Vector 개수·차원·유효숫자를 검증하고 정규화한 후에만 저장합니다.

모델 목록과 가용성은 `GET /api/admin/llm/models`, 어드민 단일 실행은
`POST /api/admin/llm/run`에서 확인합니다. 메인 페이지는 `GET /api/llm/models`로
Catalog를 읽고 `POST /api/conversations/{conversation_id}/messages`로 선택한
`model_id`를 전달합니다. 자세한 연동 방법은
`docs/3_flow/12_FLW_MainLLM_메인페이지연동가이드_20260831.md`를 참고합니다.

## 8. 자주 발생하는 문제

### `run.bat`에서 Python 3.12 오류가 표시되는 경우

기존 `backend/.venv`가 다른 Python 버전으로 생성된 상태입니다. 기존 가상환경을 정리한 뒤 Python 3.12로 다시 생성하고 `requirements.txt`를 설치합니다.

### Backend 패키지 누락 오류가 표시되는 경우

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### `frontend/node_modules` 오류가 표시되는 경우

```powershell
cd frontend
npm.cmd install
cd ..
```

### 포트가 이미 사용 중인 경우

기존에 실행 중인 Backend(8000) 또는 Frontend(5173) 프로세스를 종료한 뒤 `run.bat`을 다시 실행합니다.

### LLM 카드가 비활성화되는 경우

Vast.ai Notebook의 5개 모델 로드, 인증된 `GET /health`, 8000번 컨테이너 포트의 공개 포트 매핑, `.env`의 `LLM_REMOTE_BASE_URL`·`LLM_REMOTE_API_KEY`를 확인합니다. 브라우저에서 `/health`를 직접 열었을 때 401이 나오는 것은 Authorization 헤더가 없기 때문이며 정상입니다. 준비된 Notebook은 `scripts/vastai_medical_llm_server.ipynb`입니다.
