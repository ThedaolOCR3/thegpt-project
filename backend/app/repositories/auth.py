import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generated import Users


class AuthRepository:
    """인증 기능에 필요한 DB 접근만 담당합니다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_user_by_email(self, email: str) -> Users | None:
        return self.db.scalar(select(Users).where(Users.email == email))

    def find_user_by_id(self, user_id: str) -> Users | None:
        return self.db.get(Users, UUID(user_id))

    def create_guest_user(self) -> Users:
        # 로그인 수단이 없는 임시 계정. email UNIQUE 제약을 만족시키려고 플레이스홀더
        # 도메인 + uuid를 쓴다 (실제로 발송/수신되지 않는 주소).
        # 주의: .local/.invalid/.test 등은 email-validator가 예약 도메인으로 막아버려서
        # (EmailStr 검증 실패) 못 쓴다 — .internal은 통과한다.
        placeholder_email = f"guest-{uuid.uuid4()}@guest.thegpt.internal"
        user = Users(
            email=placeholder_email,
            password_hash=None,
            auth_provider="guest",
            is_email_verified=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
