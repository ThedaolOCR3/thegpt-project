from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.generated import Users
from app.repositories.auth import AuthRepository
from app.schemas.auth import LoginResponse, UserResponse

password_hash = PasswordHash.recommended()


def to_user_response(user: Users) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile_image_url=user.profile_image_url,
        is_email_verified=bool(user.is_email_verified),
        # DB에 관리자 컬럼이 없는 환경에서는 일반 사용자로 처리합니다.
        is_admin=bool(getattr(user, "is_admin", False)),
    )


class AuthService:
    """회원가입, 인증, 로그인 규칙을 한곳에서 관리합니다."""

    def __init__(self, db: Session) -> None:
        self.repository = AuthRepository(db)

    def login(self, email: str, password: str) -> LoginResponse:
        user = self.repository.find_user_by_email(email.lower().strip())
        if not user or not user.password_hash or not password_hash.verify(password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_email_verified:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "이메일 인증을 먼저 완료해주세요.")

        expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        token = jwt.encode(
            {"sub": str(user.id), "exp": expires_at},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return LoginResponse(access_token=token, user=to_user_response(user))
