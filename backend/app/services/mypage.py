from fastapi import HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.models.generated import Users
from app.repositories.mypage import MyPageRepository
from app.schemas.auth import (
    DeleteAccountResponse,
    DeleteConsultationsResponse,
    UsageSummaryResponse,
)

password_hash = PasswordHash.recommended()


class MyPageService:
    def __init__(self, db: Session) -> None:
        self.repository = MyPageRepository(db)

    def usage_summary(self, user: Users) -> UsageSummaryResponse:
        count, last_at = self.repository.usage_summary(user)
        return UsageSummaryResponse(consultation_count=count, last_consultation_at=last_at)

    def delete_account(self, user: Users, password: str) -> DeleteAccountResponse:
        if not user.password_hash or not password_hash.verify(password, user.password_hash):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "비밀번호가 올바르지 않습니다.")
        self.repository.delete_account(user)
        return DeleteAccountResponse(message="회원 탈퇴가 완료됐습니다.")

    def delete_all_consultations(self, user: Users) -> DeleteConsultationsResponse:
        deleted_count = self.repository.delete_all_consultations(user)
        return DeleteConsultationsResponse(
            message="모든 상담 데이터가 삭제됐습니다.",
            deleted_count=deleted_count,
        )
