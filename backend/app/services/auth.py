from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.generated import Users
from app.repositories.auth import AuthRepository
from app.repositories.guest_throttle import GuestThrottleRepository
from app.schemas.auth import LoginResponse, UserResponse

password_hash = PasswordHash.recommended()
logger = get_logger("services.auth")


def to_user_response(user: Users) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile_image_url=user.profile_image_url,
        is_email_verified=bool(user.is_email_verified),
        # DB에 관리자 컬럼이 없는 환경에서는 일반 사용자로 처리합니다.
        is_admin=bool(getattr(user, "is_admin", False)),
        created_at=user.created_at,
        has_password=bool(user.password_hash),
    )


def create_access_token(user_id: str, expire_minutes: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


class AuthService:
    """회원가입, 인증, 로그인 규칙을 한곳에서 관리합니다."""

    def __init__(self, db: Session) -> None:
        self.repository = AuthRepository(db)
        self.guest_throttle = GuestThrottleRepository(db)

    def login(self, email: str, password: str) -> LoginResponse:
        user = self.repository.find_user_by_email(email.lower().strip())
        if not user or not user.password_hash or not password_hash.verify(password, user.password_hash):
            logger.warning("로그인 실패 (이메일/비밀번호 불일치): email=%s", email)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_email_verified:
            logger.warning("로그인 실패 (이메일 미인증): email=%s", email)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "이메일 인증을 먼저 완료해주세요.")

        token = create_access_token(str(user.id), settings.access_token_expire_minutes)
        return LoginResponse(access_token=token, user=to_user_response(user))

    def create_guest_session(self, client_ip: str) -> LoginResponse:
        """비로그인 사용자가 채팅을 쓸 수 있도록 임시 계정을 발급합니다.

        기존 users/conversations/messages 테이블을 그대로 재사용하고
        auth_provider='guest'로만 구분하므로 스키마 변경이 필요 없다.

        브라우저는 발급받은 토큰을 localStorage에 캐싱해서 재사용하지만, 시크릿창/
        다른 브라우저를 쓰면 매번 새 게스트 계정을 받을 수 있어서
        guest_message_limit을 사실상 무제한으로 우회할 수 있다(완전히 막을 순
        없음 - 익명 사용자라 신원 자체가 없어서). 같은 IP에서 짧은 시간에 새
        게스트 계정을 너무 많이 만드는 것만 제한한다.
        """
        allowed = self.guest_throttle.check_and_increment(
            client_ip,
            limit=settings.guest_signup_limit_per_ip,
            window_hours=settings.guest_signup_window_hours,
        )
        if not allowed:
            logger.warning("게스트 계정 발급 제한 (IP당 한도 초과): ip=%s", client_ip)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "일시적으로 게스트 계정을 너무 많이 만들었습니다. 잠시 후 다시 시도해주세요.",
            )

        user = self.repository.create_guest_user()
        token = create_access_token(str(user.id), settings.guest_token_expire_minutes)
        return LoginResponse(access_token=token, user=to_user_response(user))
