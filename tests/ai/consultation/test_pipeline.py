import unittest
from dataclasses import dataclass

from ai.consultation.pipeline import DISCLAIMER, FALLBACK_ANSWER, consult


@dataclass
class FakeResult:
    answer: str


@dataclass
class FakeExecution:
    result: FakeResult


class FakeLlmApplication:
    """llm_application.run()만 흉내내는 최소 stub — 실제 모델을 안 띄운다."""

    def __init__(self, answer: str | None = None, raise_error: bool = False) -> None:
        self._answer = answer
        self._raise_error = raise_error
        self.last_model_id: str | None = None

    async def run(self, model_id, request):  # noqa: ANN001 - 테스트 stub
        self.last_model_id = model_id
        if self._raise_error:
            raise RuntimeError("모델을 사용할 수 없습니다.")
        return FakeExecution(result=FakeResult(answer=self._answer or "괜찮아지실 거예요."))


class ConsultTest(unittest.IsolatedAsyncioTestCase):
    async def test_normal_answer_gets_disclaimer_exactly_once(self) -> None:
        app = FakeLlmApplication(answer="충분한 휴식을 취해보세요.")
        result = await consult(app, "콧물이 나요")

        self.assertTrue(result.answer.startswith("충분한 휴식을 취해보세요."))
        self.assertEqual(result.answer.count(DISCLAIMER.strip()), 1)

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
