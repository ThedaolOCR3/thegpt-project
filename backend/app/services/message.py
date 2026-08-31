import asyncio
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ai.consultation import ConsultationResult, consult
from ai.rag import RetrievedChunk
from app.core.config import settings
from app.core.logging import get_logger
from app.models.generated import Conversations, Messages, Users
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageAttachmentInput, MessageAttachmentResponse, MessageResponse
from app.services import rag_search_service
from app.services.conversation import ConversationService
from app.services.llm_runtime import llm_application

logger = get_logger("services.message")

# 채팅·일반 LLM API·Admin 비교 API가 공통 Runtime을 공유한다.


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


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations_service = ConversationService(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)

    def list_messages(self, conversation_id: str, user_id: UUID) -> list[MessageResponse]:
        conversation = self.conversations_service.get_owned(conversation_id, user_id)
        messages = self.messages.list_by_conversation(conversation.id)
        return [to_message_response(m) for m in messages]

    async def send_message(
        self,
        conversation_id: str,
        current_user: Users,
        content: str,
        attachments: list[MessageAttachmentInput] | None = None,
        model_id: str | None = None,
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

        reply_content = await self._generate_reply(content, conversation, model_id)

        assistant_message = self.messages.create(conversation.id, "assistant", reply_content)
        self.conversations.touch(conversation)
        return to_message_response(assistant_message)

    async def _generate_reply(
        self, content: str, conversation: Conversations, model_id: str | None = None
    ) -> str:
        # 텍스트가 없고 첨부파일만 있는 경우(OCR 미연동 상태라 첨부 내용을 알 수 없음)엔
        # LLM 호출 자체가 의미 없어서 안내 문구만 반환한다.
        if not content:
            return "첨부해주신 파일은 확인했어요. 증상이나 궁금하신 점을 글로도 함께 적어주시면 더 정확히 답변드릴 수 있어요."

        reference_chunks = await asyncio.to_thread(self._search_reference_chunks, content)

        consult_kwargs = {"model_id": model_id} if model_id else {}
        result: ConsultationResult = await consult(
            llm_application, content, reference_chunks=reference_chunks, **consult_kwargs
        )

        if result.department:
            self.conversations.set_category_if_unset(conversation, result.department)

        return result.answer

    def _search_reference_chunks(self, query: str) -> list[RetrievedChunk]:
        """RAG 검색 결과를 consult()의 참고 의료 정보로 넘긴다. RAG 데이터셋이 아직
        Neon에 안 들어갔거나(테이블은 있는데 0건) 마이그레이션 자체가 아직 안
        적용된 경우(테이블 없음) 등 어떤 이유로든 검색이 실패해도, 여기서 잡아서
        빈 결과를 반환한다 — consult()는 빈/None 결과를 "참고 정보 없음" 경로로
        처리하므로 채팅은 LLM+프롬프트 엔지니어링만으로 계속 응답한다(안 죽음).
        나중에 실제 데이터가 채워지면 이 함수는 코드 변경 없이 그대로 검색 결과를
        반환하기 시작한다."""
        try:
            return rag_search_service.search(self.db, query)
        except Exception:
            logger.exception("RAG 검색 실패 — 참고 정보 없이 LLM/프롬프트만으로 응답을 이어감: query=%r", query)
            # DB 오류(예: 마이그레이션 전이라 chunk_embeddings 테이블이 아직 없음)는
            # Postgres 트랜잭션 자체를 abort 상태로 만든다 — rollback을 안 하면 이후
            # 이 요청에서 하는 모든 DB 작업(응답 메시지 저장 등)이 함께 실패한다.
            self.db.rollback()
            return []

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
