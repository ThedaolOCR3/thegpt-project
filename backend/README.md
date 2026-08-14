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

`ai/ocr`, `ai/rag`는 backend/scripts/Colab이 공통으로 쓰는 독립 패키지다. backend에서
쓰려면 이 저장소 루트에서 editable 설치가 한 번 필요하다 (repo root의 `pyproject.toml` 참고):

```bash
cd backend
.venv\Scripts\pip install -e ..
.venv\Scripts\pip install -r ../ai/requirements.txt  # 무거움(torch, paddleocr 등) — 필요할 때만
```

자세한 내용은 `ai/ocr/CLAUDE.md`, `ai/rag/CLAUDE.md` 참고.

로컬에서 OCR/임베딩/하이브리드 검색 파이프라인을 직접 테스트해보고 싶으면
`backend/local_lab/`(git 미포함, 개인 로컬 전용)에 라우터+페이지를 만들어서 위 `ai/`
패키지를 호출하는 방식을 쓴다 — `APP_ENV=local`일 때만 `/local-lab`에 자동으로 붙는다.

## 로그인과 이메일 인증

SMTP 및 이메일 인증의 자세한 흐름은 `docs/email-verification.md`를 참고하세요.

비밀번호 재설정 링크 발송과 토큰 처리 흐름은 `docs/password-reset.md`를 참고하세요.
