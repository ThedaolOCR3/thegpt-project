from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.password_reset import ForgotPasswordRequest, PasswordResetMessage, ResetPasswordRequest
from app.services.password_reset import PasswordResetService

router = APIRouter()


@router.post("/forgot-password", response_model=PasswordResetMessage)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetMessage:
    return PasswordResetService(db).request_reset(payload.email)


@router.post("/reset-password", response_model=PasswordResetMessage)
def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetMessage:
    return PasswordResetService(db).reset_password(payload.token, payload.new_password)
