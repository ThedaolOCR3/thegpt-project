from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger

logger = get_logger("main")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(Exception)
    async def log_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        # HTTPException(401/404/429 등 의도된 실패)은 여기까지 안 옴 — 진짜 버그/DB
        # 오류 같은 처리 못한 예외만 여기서 함수명(엔드포인트)+시각+에러내용으로 기록.
        logger.exception("처리되지 않은 예외: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "서버 오류가 발생했습니다."})

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db", tags=["health"])
    def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}

    return app


app = create_app()
