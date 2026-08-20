# Backend

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/health
- DB 상태 확인: http://localhost:8000/health/db

프로젝트 최상위 `.env`의 `DATABASE_URL`을 Neon 콘솔에서 복사한 연결 문자열로 교체합니다.
Backend는 실행 디렉터리와 관계없이 이 최상위 파일 하나만 읽습니다.

## OCR 문서 처리

- PDF: Native Text와 포함 이미지를 구분하는 Hybrid PDF 처리
- PNG/JPG: PaddleOCR 처리
- DOCX: `python-docx` 기반 문단·표·이미지 직접 추출
- PPTX: `python-pptx` 기반 슬라이드·도형·표·이미지·발표자 노트 직접 추출

DOCX/PPTX 처리를 위해 LibreOffice를 설치하거나 실행 경로를 설정할 필요가 없습니다.
정확한 Office 페이지 미리보기 또는 페이지 번호가 필요하면 원본 프로그램에서 PDF로
내보낸 뒤 PDF를 업로드합니다.

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

## 로그인과 이메일 인증

SMTP 및 이메일 인증의 자세한 흐름은 `docs/email-verification.md`를 참고하세요.

비밀번호 재설정 링크 발송과 토큰 처리 흐름은 `docs/password-reset.md`를 참고하세요.

R2 프로필 이미지 저장소 설정은 `docs/r2-profile-images.md`를 참고하세요.
