from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.generated import Messages, Users
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageAttachmentInput, MessageAttachmentResponse, MessageResponse
from app.services.conversation import ConversationService

logger = get_logger("services.message")


def to_message_response(message: Messages) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        attachments=[
            MessageAttachmentResponse(
                id=str(a.id),
                file_name=a.file_name,
                file_type=a.file_type,
                file_size_bytes=a.file_size_bytes,
            )
            for a in message.message_attachments
        ],
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

    def send_message(
        self,
        conversation_id: str,
        current_user: Users,
        content: str,
        attachments: list[MessageAttachmentInput] | None = None,
    ) -> MessageResponse:
        attachments = attachments or []
        content = content.strip()
        if not content and not attachments:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "메시지 내용이나 첨부파일이 필요합니다.")

        conversation = self.conversations_service.get_owned(conversation_id, current_user.id)
        self._check_guest_limits(current_user, new_attachment_count=len(attachments))

        is_first_message = len(self.messages.list_by_conversation(conversation.id)) == 0

        user_message = self.messages.create(conversation.id, "user", content)
        if attachments:
            self.messages.create_attachments(
                user_message.id, [a.model_dump() for a in attachments]
            )

        if is_first_message and not conversation.is_title_custom:
            self.conversations.set_auto_title(conversation, content or attachments[0].name)

        assistant_message = self.messages.create(
            conversation.id, "assistant", _generate_placeholder_reply(content)
        )
        self.conversations.touch(conversation)
        return to_message_response(assistant_message)

    def _check_guest_limits(self, current_user: Users, new_attachment_count: int) -> None:
        if current_user.auth_provider != "guest":
            return

        sent = self.messages.count_user_messages_total(current_user.id)
        if sent >= settings.guest_message_limit:
            logger.info("게스트 메시지 한도 초과: user_id=%s sent=%s", current_user.id, sent)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"게스트는 최대 {settings.guest_message_limit}개의 메시지를 보낼 수 있어요. "
                "로그인하면 이어서 이용할 수 있어요.",
            )

        if new_attachment_count:
            attached = self.messages.count_user_attachments_total(current_user.id)
            if attached + new_attachment_count > settings.guest_attachment_limit:
                logger.info("게스트 첨부파일 한도 초과: user_id=%s attached=%s", current_user.id, attached)
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"게스트는 최대 {settings.guest_attachment_limit}개의 파일을 첨부할 수 있어요. "
                    "로그인하면 이어서 이용할 수 있어요.",
                )
