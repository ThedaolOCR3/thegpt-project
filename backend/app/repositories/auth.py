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
