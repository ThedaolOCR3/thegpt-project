import unittest

from ai.consultation.response_validator import validate


class ValidateTest(unittest.TestCase):
    def test_leaves_safe_answer_unchanged(self) -> None:
        answer = "충분한 휴식과 수분 섭취가 도움이 될 수 있습니다."
        self.assertEqual(validate(answer), answer)

    def test_appends_warning_for_mg_dosage(self) -> None:
        answer = "타이레놀 500mg을 복용하세요."
        result = validate(answer)
        self.assertIn(answer, result)
        self.assertIn("[안전 안내]", result)

    def test_appends_warning_for_tablet_count(self) -> None:
        result = validate("하루 3정씩 드세요.")
        self.assertIn("[안전 안내]", result)

    def test_does_not_false_positive_on_unrelated_text(self) -> None:
        answer = "정확한 진단을 위해 의료진과 상담하는 것이 좋습니다."
        self.assertEqual(validate(answer), answer)


if __name__ == "__main__":
    unittest.main()
