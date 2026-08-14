from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.generated import Conversations, Messages


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_conversation(self, conversation_id: UUID) -> list[Messages]:
        stmt = (
            select(Messages)
            .where(Messages.conversation_id == conversation_id)
            .order_by(Messages.created_at.asc())
        )
        return list(self.db.scalars(stmt))

    def create(self, conversation_id: UUID, role: str, content: str) -> Messages:
        message = Messages(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def count_user_messages_today(self, user_id: UUID) -> int:
        """게스트 일일 전송량 제한에 쓰는, 해당 유저가 오늘 보낸 user 메시지 수."""
        start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count(Messages.id))
            .join(Conversations, Messages.conversation_id == Conversations.id)
            .where(
                Conversations.user_id == user_id,
                Messages.role == "user",
                Messages.created_at >= start_of_day,
            )
        )
        return self.db.scalar(stmt) or 0
