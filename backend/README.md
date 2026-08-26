# Backend

## 실행

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/health
- DB 상태 확인: http://localhost:8000/health/db

프로젝트 최상위 `.env`의 `DATABASE_URL`을 Neon 콘솔에서 복사한 연결 문자열로 교체합니다.
Backend는 실행 디렉터리와 관계없이 이 최상위 파일 하나만 읽습니다.

## LLM Provider

Admin LLM과 일반 LLM API는 `ai/llm`의 공통 Provider 계약과 Model Registry를 사용합니다.

- 실제: Ollama `gemma3:1b`, Gemini `gemini-3.5-flash-lite`
- Mock: `medgemma`, `gemma`, `qwen`, `llama`

Ollama 모델은 `ollama pull gemma3:1b`로 직접 준비하고, Gemini 키는 최상위 `.env`의 `GEMINI_API_KEY`에 개발자별로 설정합니다. API 키는 Frontend로 전달하거나 로그에 기록하지 않습니다.

Backend의 `app/services/admin_llm.py`는 환경변수를 공통 Core 설정으로 변환하고 Admin
Schema를 조립합니다. `app/services/llm_service.py`는 기존 `/api/llm/*` 계약을 공통
Core에 연결합니다. Provider 구현과 실행 순서는 `ai/llm`에만 존재합니다.

CPU Backend는 `ai/llm/requirements-api.txt`만 설치합니다. CUDA 환경에서 MedGemma
LoRA 추론까지 실행할 때는 `ai/llm/requirements-medgemma.txt`를 추가로 설치합니다.
모델 목록 조회만으로 MedGemma Base Model이나 Adapter를 로드하지 않습니다.

## OCR 문서 처리

두 OCR Endpoint는 `app/services/ocr_workflow.py`를 거쳐 같은 `ai.ocr.analyze_document()`를 호출합니다.

- PDF: Native Text와 포함 이미지를 구분하는 Digital/Scanned/Hybrid 처리
- PNG/JPG: PaddleOCR 처리
- DOCX: `python-docx` 기반 문단·표·이미지 직접 추출
- PPTX: `python-pptx` 기반 슬라이드·도형·표·이미지·발표자 노트 직접 추출

DOCX/PPTX 처리를 위해 LibreOffice를 설치하거나 실행 경로를 설정할 필요가 없습니다.
정확한 Office 페이지 미리보기 또는 페이지 번호가 필요하면 원본 프로그램에서 PDF로
내보낸 뒤 PDF를 업로드합니다.

OCR Core는 동기 CPU 작업이며 Backend Adapter가 `asyncio.to_thread()`로 실행해 FastAPI Event Loop를 직접 막지 않습니다. Admin 문자 Chunk, Job 상태와 Vector Save는 Backend에 남아 있습니다.

## 마이그레이션

```bash
alembic revision --autogenerate -m "create tables"
alembic upgrade head
```

## 기존 Neon 스키마에서 모델 생성

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/generate_models.py
```

생성 결과는 `app/models/generated.py`에 저장됩니다. 생성된 모델을 검토한 후
`app/models/__init__.py`에서 import하면 Alembic이 해당 모델을 인식합니다.

## ai/ 패키지 (OCR·RAG·LLM)

`ai/ocr`, `ai/rag`는 backend/scripts/Colab이 공통으로 쓰는 독립 패키지다. `requirements.txt`
설치만으로는 `ai` 패키지 자체가 import 가능해지지 않는다 — 저장소 루트를 editable로
한 번 더 설치해야 한다 (repo root의 `pyproject.toml` 참고):

```bash
cd backend
.venv\Scripts\pip install -e ..
.venv\Scripts\pip install -r requirements.txt   # ai/ocr 의존성(paddleocr 등)까지 같이 설치됨
```

`ai/rag`(임베딩/하이브리드 검색, torch 포함이라 더 무거움)까지 쓰려면 추가로:
```bash
.venv\Scripts\pip install -r ../ai/rag/requirements.txt
```

자세한 내용은 `ai/ocr/CLAUDE.md`, `ai/rag/CLAUDE.md`와
`docs/3_flow/11_FLW_LLM_AI코어이관코드비교_20260826.md`를 참고합니다.

⚠️ `ai/ocr`가 `backend/requirements.txt`에 들어가 있어서 documents API의 OCR 기능이
지금은 backend 프로세스 안에서 그대로 돈다 — paddlepaddle만 수백MB라 Docker 이미지가
꽤 커지고, 무료 티어처럼 리소스가 빠듯한 배포 환경에서는 메모리가 부족할 수 있다.
실제 배포 전에 OCR을 별도 워커/서비스로 분리할지 검토할 것.

로컬에서 OCR/임베딩/하이브리드 검색 파이프라인을 직접 테스트해보고 싶으면
`backend/local_lab/`(git 미포함, 개인 로컬 전용)에 라우터+페이지를 만들어서 위 `ai/`
패키지를 호출하는 방식을 쓴다 — `APP_ENV=local`일 때만 `/local-lab`에 자동으로 붙는다.

## 로그인과 이메일 인증

SMTP 및 이메일 인증의 자세한 흐름은 `docs/email-verification.md`를 참고하세요.

비밀번호 재설정 링크 발송과 토큰 처리 흐름은 `docs/password-reset.md`를 참고하세요.

R2 프로필 이미지 저장소 설정은 `docs/r2-profile-images.md`를 참고하세요.
