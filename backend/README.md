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
