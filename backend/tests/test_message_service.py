import unittest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.services import message as message_module
from app.services.message import MessageService


def _bare_service(db) -> MessageService:
    # ConversationService/ConversationRepository/MessageRepository는 진짜 DB 쿼리를
    # 하므로, 여기서 테스트하려는 RAG/모델 선택 로직만 떼어내기 위해 __init__을
    # 건너뛰고 필요한 속성만 채운다.
    service = MessageService.__new__(MessageService)
    service.db = db
    service.conversations = MagicMock()
    service.consultation_logs = MagicMock()
    return service


class SearchReferenceChunksTest(unittest.TestCase):
    def test_returns_search_result_on_success(self) -> None:
        db = MagicMock()
        service = _bare_service(db)
        fake_chunks = [object()]
        with patch.object(message_module.rag_search_service, "search", return_value=fake_chunks):
            result = service._search_reference_chunks("두통이 있어요")
        self.assertEqual(result, fake_chunks)
        db.rollback.assert_not_called()

    def test_swallows_exception_and_rolls_back_session(self) -> None:
        # chunk_embeddings 테이블이 아직 마이그레이션 안 된 경우 등을 흉내낸다 —
        # 검색이 실패해도 빈 리스트를 반환하고, DB 세션을 롤백해서 이후 이 요청의
        # 다른 DB 작업(응답 메시지 저장 등)이 "트랜잭션 abort" 상태로 실패하지
        # 않게 해야 한다.
        db = MagicMock()
        service = _bare_service(db)
        with patch.object(
            message_module.rag_search_service, "search", side_effect=RuntimeError("relation does not exist")
        ):
            result = service._search_reference_chunks("두통이 있어요")
        self.assertEqual(result, [])
        db.rollback.assert_called_once()


class GenerateReplyTest(unittest.IsolatedAsyncioTestCase):
    async def test_empty_content_returns_canned_text_without_touching_rag_or_llm(self) -> None:
        service = _bare_service(MagicMock())
        with (
            patch.object(message_module, "consult") as mock_consult,
            patch.object(message_module.rag_search_service, "search") as mock_search,
        ):
            reply, result = await service._generate_reply("", conversation=MagicMock())

        self.assertIn("첨부해주신 파일", reply)
        self.assertIsNone(result)  # 실제 상담이 아니므로 대시보드 로그 대상이 아님
        mock_consult.assert_not_called()
        mock_search.assert_not_called()

    async def test_model_id_is_forwarded_to_consult_when_given(self) -> None:
        service = _bare_service(MagicMock())
        fake_result = message_module.ConsultationResult(answer="답변", department=None, confidence="낮음")
        with (
            patch.object(message_module, "consult", return_value=fake_result) as mock_consult,
            patch.object(message_module.rag_search_service, "search", return_value=[]),
        ):
            await service._generate_reply("질문", conversation=MagicMock(), model_id="qwen")

        self.assertEqual(mock_consult.call_args.kwargs.get("model_id"), "qwen")

    async def test_no_model_id_does_not_pass_model_id_kwarg(self) -> None:
        # model_id를 안 보내면 consult()의 기본값(DEFAULT_MODEL_ID)이 그대로 적용돼야
        # 한다 — 여기서 None을 넘기면 consult()가 "model_id=None"으로 오해할 수 있다.
        service = _bare_service(MagicMock())
        fake_result = message_module.ConsultationResult(answer="답변", department=None, confidence="낮음")
        with (
            patch.object(message_module, "consult", return_value=fake_result) as mock_consult,
            patch.object(message_module.rag_search_service, "search", return_value=[]),
        ):
            await service._generate_reply("질문", conversation=MagicMock())

        self.assertNotIn("model_id", mock_consult.call_args.kwargs)

    async def test_department_result_sets_category_if_unset(self) -> None:
        service = _bare_service(MagicMock())
        fake_result = message_module.ConsultationResult(answer="답변", department="내과", confidence="높음")
        conversation = MagicMock()
        with (
            patch.object(message_module, "consult", return_value=fake_result),
            patch.object(message_module.rag_search_service, "search", return_value=[]),
        ):
            await service._generate_reply("질문", conversation=conversation)

        service.conversations.set_category_if_unset.assert_called_once_with(conversation, "내과")


class LogConsultationTest(unittest.TestCase):
    def test_success_writes_log_via_repository(self) -> None:
        db = MagicMock()
        service = _bare_service(db)
        result = message_module.ConsultationResult(answer="답변", department="내과", confidence="높음")
        user_id, conversation_id, message_id = uuid4(), uuid4(), uuid4()

        service._log_consultation(user_id, conversation_id, message_id, result)

        service.consultation_logs.create.assert_called_once_with(
            user_id=user_id, conversation_id=conversation_id, message_id=message_id, result=result
        )
        db.rollback.assert_not_called()

    def test_failure_is_swallowed_and_rolls_back_without_raising(self) -> None:
        # 대시보드 로그 저장이 실패해도(DB 오류 등) 이미 사용자에게 나갈 응답은
        # 정해진 뒤라 — 절대 예외를 밖으로 던지면 안 된다(채팅 자체가 깨짐).
        db = MagicMock()
        service = _bare_service(db)
        service.consultation_logs.create.side_effect = RuntimeError("DB unavailable")
        result = message_module.ConsultationResult(answer="답변", department=None, confidence="낮음")

        try:
            service._log_consultation(uuid4(), uuid4(), uuid4(), result)
        except Exception:  # noqa: BLE001 - 여기서 예외가 나오면 테스트 자체가 실패해야 함
            self.fail("_log_consultation이 예외를 밖으로 던지면 안 됨")

        db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
