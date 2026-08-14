from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.generated import Messages, Users
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageResponse
from app.services.conversation import ConversationService


def to_message_response(message: Messages) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


# TODO: ai/consultation(증상 -> 질병/진료과/처방)이 붙기 전까지 쓰는 임시 응답.
# 실제 RAG/LLM 연동 시 이 함수만 교체하면 나머지 흐름(저장/조회)은 그대로 재사용 가능하다.
def _generate_placeholder_reply(user_content: str) -> str:
    return (
        f'"{user_content}"에 대해 확인했어요. '
        "AI 진료상담 로직은 아직 연동 준비 중이라 임시 응답을 드리고 있어요."
    )


class MessageService:
    def __init__(self, db: Session) -> None:
        self.conversations_service = ConversationService(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)

    def list_messages(self, conversation_id: str, user_id: UUID) -> list[MessageResponse]:
        conversation = self.conversations_service.get_owned(conversation_id, user_id)
        messages = self.messages.list_by_conversation(conversation.id)
        return [to_message_response(m) for m in messages]

    def send_message(self, conversation_id: str, current_user: Users, content: str) -> MessageResponse:
        conversation = self.conversations_service.get_owned(conversation_id, current_user.id)
        self._check_guest_limit(current_user)

        self.messages.create(conversation.id, "user", content)
        assistant_message = self.messages.create(
            conversation.id, "assistant", _generate_placeholder_reply(content)
        )
        self.conversations.touch(conversation)
        return to_message_response(assistant_message)

    def _check_guest_limit(self, current_user: Users) -> None:
        if current_user.auth_provider != "guest":
            return
        sent_today = self.messages.count_user_messages_today(current_user.id)
        if sent_today >= settings.guest_daily_message_limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"게스트는 하루 최대 {settings.guest_daily_message_limit}개의 메시지를 보낼 수 있어요. "
                "로그인하면 제한 없이 이용할 수 있어요.",
            )
