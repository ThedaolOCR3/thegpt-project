import unittest
from dataclasses import dataclass

from ai.consultation.classifier import DepartmentResult
from ai.consultation.pipeline import DEFAULT_MAX_OUTPUT_TOKENS, FALLBACK_ANSWER, consult


@dataclass
class FakeResult:
    answer: str
    finish_reason: str | None = None


@dataclass
class FakeExecution:
    result: FakeResult


class FakeLlmApplication:
    """llm_application.run()만 흉내내는 최소 stub — 실제 모델을 안 띄운다."""

    def __init__(
        self,
        answer: str | None = None,
        raise_error: bool = False,
        finish_reason: str | None = None,
    ) -> None:
        self._answer = answer
        self._raise_error = raise_error
        self._finish_reason = finish_reason
        self.last_model_id: str | None = None
        self.last_request = None

    async def run(self, model_id, request):  # noqa: ANN001 - 테스트 stub
        self.last_model_id = model_id
        self.last_request = request
        if self._raise_error:
            raise RuntimeError("모델을 사용할 수 없습니다.")
        return FakeExecution(
            result=FakeResult(answer=self._answer or "괜찮아지실 거예요.", finish_reason=self._finish_reason)
        )


class ConsultTest(unittest.IsolatedAsyncioTestCase):
    async def test_normal_answer_has_no_disclaimer_text(self) -> None:
        # 면책 문구는 이제 프론트엔드가 채팅 UI 배너로 보여준다 — 매 답변 텍스트에
        # 반복해서 붙이지 않는다(MessageBubble.tsx 참고).
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요")

        self.assertEqual(result.answer, "충분한 휴식을 취해보세요.")
        self.assertNotIn("※", result.answer)

    async def test_requests_max_output_tokens_to_avoid_mid_sentence_cutoff(self) -> None:
        # 실제 관찰된 사례 - Vast.ai 서버의 max_output_tokens 기본값(256)만 쓰면
        # 공감+원인+확인질문+주의사항을 다 담는 답변이 문장 중간에 잘렸다("...정확한
        # 진단 후 적절한"에서 끊김). 서버가 허용하는 최댓값을 명시적으로 요청해야 한다.
        app = FakeLlmApplication(answer="답변")
        await consult(app, "어깨가 아파요")

        self.assertEqual(app.last_request.max_output_tokens, DEFAULT_MAX_OUTPUT_TOKENS)

    async def test_llm_failure_returns_fallback_without_disclaimer(self) -> None:
        app = FakeLlmApplication(raise_error=True)
        result = await consult(app, "콧물이 나요")

        self.assertEqual(result.answer, FALLBACK_ANSWER)
        self.assertNotIn("※", result.answer)

    async def test_emergency_keyword_short_circuits_without_calling_llm(self) -> None:
        app = FakeLlmApplication()
        result = await consult(app, "갑자기 숨쉬기 힘들어요")

        self.assertIsNone(app.last_model_id)  # LLM이 아예 호출되지 않았어야 한다.
        self.assertIn("119", result.answer)
        self.assertIsNone(result.department)

    async def test_risky_dosage_in_llm_answer_gets_extra_warning(self) -> None:
        app = FakeLlmApplication(answer="타이레놀 500mg을 드세요.")
        result = await consult(app, "머리가 아파요")

        self.assertIn("[안전 안내]", result.answer)

    async def test_success_populates_dashboard_metadata(self) -> None:
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요", model_id="qwen-medical")

        self.assertEqual(result.model_id, "qwen-medical")
        self.assertFalse(result.is_fallback)
        self.assertFalse(result.is_emergency)
        self.assertIsNone(result.error_type)
        self.assertIsNotNone(result.response_time_ms)
        self.assertGreaterEqual(result.response_time_ms, 0)

    async def test_reference_chunks_set_rag_hit_count(self) -> None:
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        chunks = [object(), object(), object()]
        result = await consult(app, "콧물이 나요", reference_chunks=chunks)

        self.assertEqual(result.rag_hit_count, 3)

    async def test_no_reference_chunks_means_zero_rag_hit_count(self) -> None:
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요")

        self.assertEqual(result.rag_hit_count, 0)

    async def test_llm_failure_sets_fallback_flag_and_error_type(self) -> None:
        app = FakeLlmApplication(raise_error=True)
        result = await consult(app, "콧물이 나요")

        self.assertTrue(result.is_fallback)
        self.assertEqual(result.error_type, "RuntimeError")

    async def test_emergency_short_circuit_sets_emergency_flag(self) -> None:
        app = FakeLlmApplication()
        result = await consult(app, "갑자기 숨쉬기 힘들어요")

        self.assertTrue(result.is_emergency)
        self.assertFalse(result.is_fallback)
        self.assertIsNone(result.model_id)  # LLM을 아예 안 불렀으므로 model_id도 없음

    async def test_finish_reason_is_forwarded_from_provider_result(self) -> None:
        # "length"는 max_output_tokens에 걸려 답변이 중간에 잘렸다는 뜻 - 대시보드가
        # 이 비율을 집계하려면 여기서부터 값이 살아있어야 한다.
        app = FakeLlmApplication(answer="답변", finish_reason="length")
        result = await consult(app, "콧물이 나요")

        self.assertEqual(result.finish_reason, "length")

    async def test_finish_reason_is_none_when_not_provided_by_stub(self) -> None:
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요")

        self.assertIsNone(result.finish_reason)

    async def test_emergency_short_circuit_leaves_finish_reason_none(self) -> None:
        app = FakeLlmApplication()
        result = await consult(app, "갑자기 숨쉬기 힘들어요")

        self.assertIsNone(result.finish_reason)

    async def test_precomputed_department_result_is_used_without_reclassifying(self) -> None:
        # message.py가 RAG 검색의 진료과 부스트에도 같은 분류 결과를 쓰려고 미리
        # classify()를 해뒀다면, consult()는 그 결과를 그대로 써야 한다(자체
        # classifier를 아예 안 만들었는지까지 확인 - 만들면 낭비이자 이론상
        # 분류기 상태에 따라 값이 어긋날 여지를 만든다).
        app = FakeLlmApplication(answer="답변")
        precomputed = DepartmentResult(department="정형외과", confidence="높음")

        def _classifier_should_not_be_called():
            raise AssertionError("department_result를 미리 넘겼으면 classifier를 만들면 안 됨")

        result = await consult(
            app,
            "아무 증상 설명",
            department_result=precomputed,
            classifier=_classifier_should_not_be_called,  # 호출되면 TypeError로 즉시 드러남
        )

        self.assertEqual(result.department, "정형외과")
        self.assertEqual(result.confidence, "높음")

    async def test_execution_without_provider_or_tokens_leaves_them_none(self) -> None:
        # 테스트 stub(FakeExecution)처럼 provider/토큰 필드가 없는 llm_application도
        # 로깅 메타데이터 때문에 깨지면 안 된다 — 조용히 None으로 빠져야 한다.
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요")

        self.assertIsNone(result.provider_key)
        self.assertIsNone(result.input_tokens)
        self.assertIsNone(result.output_tokens)
        self.assertIsNone(result.total_tokens)


if __name__ == "__main__":
    unittest.main()
