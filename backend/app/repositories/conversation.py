from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.generated import Conversations


class ConversationRepository:
    """대화(conversation) 목록 조회/생성/수정만 담당합니다. 소유권 검사는 서비스 계층에서."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Conversations]:
        stmt = (
            select(Conversations)
            .where(Conversations.user_id == user_id)
            .order_by(Conversations.updated_at.desc())
        )
        return list(self.db.scalars(stmt))

    def create(self, user_id: UUID) -> Conversations:
        conversation = Conversations(user_id=user_id, title="새 대화", is_title_custom=False)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def find_by_id(self, conversation_id: UUID) -> Conversations | None:
        return self.db.get(Conversations, conversation_id)

    def rename(self, conversation: Conversations, title: str) -> Conversations:
        conversation.title = title
        conversation.is_title_custom = True
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversations) -> None:
        # ORM의 session.delete()는 자식 messages를 지우는 대신 conversation_id를
        # NULL로 바꾸려다 NOT NULL 제약에 걸린다 (messages 관계에 cascade 설정이 없음).
        # DB의 FK가 이미 ON DELETE CASCADE라서, raw DELETE로 그 카스케이드에 맡긴다.
        self.db.execute(delete(Conversations).where(Conversations.id == conversation.id))
        self.db.commit()

    def touch(self, conversation: Conversations) -> None:
        # updated_at에 DB 트리거가 없으므로(생성 시 server_default만 있음) 여기서 직접 갱신한다.
        conversation.updated_at = datetime.now(UTC)
        self.db.commit()

    def set_auto_title(self, conversation: Conversations, content: str) -> None:
        """첫 메시지로 제목을 자동으로 채운다. 사용자가 직접 이름을 바꾼 적 있으면
        건드리지 않는다 (is_title_custom는 유지 — 이건 '자동' 제목이라서)."""
        title = content.strip().replace("\n", " ")
        if len(title) > 40:
            title = title[:40].rstrip() + "…"
        if not title:
            return
        conversation.title = title
        self.db.commit()
