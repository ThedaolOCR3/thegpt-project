from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.generated import Users
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from app.services.auth import AuthService, to_user_response

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    return AuthService(db).login(payload.email, payload.password)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[Users, Depends(get_current_user)]) -> UserResponse:
    return to_user_response(current_user)
