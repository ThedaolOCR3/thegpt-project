import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_config import email_settings
from app.repositories.password_reset import PasswordResetRepository
from app.schemas.password_reset import PasswordResetMessage
from app.services.email import email_service

password_hash = PasswordHash.recommended()


def _password_fingerprint(value: str | None) -> str:
    """토큰에 비밀번호 원문 대신 해시의 짧은 지문만 넣습니다."""
    return hashlib.sha256((value or "").encode()).hexdigest()[:16]


class PasswordResetService:
    def __init__(self, db: Session) -> None:
        self.repository = PasswordResetRepository(db)

    def request_reset(self, email: str) -> PasswordResetMessage:
        user = self.repository.find_by_email(email.lower().strip())
        generic_message = "가입된 이메일이라면 비밀번호 재설정 링크를 발송했습니다."

        # 계정 존재 여부를 외부에 노출하지 않습니다.
        if not user or not user.password_hash:
            return PasswordResetMessage(message=generic_message)

        expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_expire_minutes)
        token = jwt.encode(
            {
                "sub": str(user.id),
                "purpose": "password_reset",
                "pwd": _password_fingerprint(user.password_hash),
                "exp": expires_at,
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        sent = email_service.send_password_reset_link(user.email, reset_url)
        return PasswordResetMessage(
            message=generic_message,
            dev_reset_url=None if sent or email_settings.app_env == "production" else reset_url,
        )

    def reset_password(self, token: str, new_password: str) -> PasswordResetMessage:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except InvalidTokenError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "재설정 링크가 유효하지 않거나 만료됐습니다.") from error

        if payload.get("purpose") != "password_reset":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "잘못된 재설정 링크입니다.")

        user = self.repository.find_by_id(payload.get("sub", ""))
        if not user or payload.get("pwd") != _password_fingerprint(user.password_hash):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "이미 사용했거나 유효하지 않은 링크입니다.")

        user.password_hash = password_hash.hash(new_password)
        user.updated_at = datetime.now(UTC)
        self.repository.save()
        return PasswordResetMessage(message="비밀번호가 변경됐습니다. 새 비밀번호로 로그인해주세요.")
