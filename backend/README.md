# Backend

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/health
- DB 상태 확인: http://localhost:8000/health/db

`.env`의 `DATABASE_URL`을 Neon 콘솔에서 복사한 연결 문자열로 교체합니다.

## 마이그레이션

```bash
alembic revision --autogenerate -m "create tables"
alembic upgrade head
```

## 기존 Neon 스키마에서 모델 생성

```bash
pip install -r requirements-dev.txt
python scripts/generate_models.py
```

생성 결과는 `app/models/generated.py`에 저장됩니다. 생성된 모델을 검토한 후
`app/models/__init__.py`에서 import하면 Alembic이 해당 모델을 인식합니다.

## ai/ 패키지 (OCR·RAG)

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

자세한 내용은 `ai/ocr/CLAUDE.md`, `ai/rag/CLAUDE.md` 참고.

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
