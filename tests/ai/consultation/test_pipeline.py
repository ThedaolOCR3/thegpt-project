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


if __name__ == "__main__":
    unittest.main()
